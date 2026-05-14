package service

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"log/slog"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/uuid"

	"github.com/mymikasa/pivot/app/kb/domain"
	"github.com/mymikasa/pivot/app/kb/repository"
	jwtpkg "github.com/mymikasa/pivot/pkg/jwt"
	"github.com/mymikasa/pivot/pkg/storage"
)

const maxFileSize = 100 * 1024 * 1024 // 100MB

const (
	presignedPutTTL = 15 * time.Minute
	presignedGetTTL = 1 * time.Hour
)

var allowedExtensions = map[string]struct{}{
	".pdf": {}, ".doc": {}, ".docx": {}, ".xls": {}, ".xlsx": {}, ".ppt": {}, ".pptx": {},
	".txt": {}, ".md": {}, ".csv": {}, ".json": {},
}

type KbService struct {
	repo    repository.Repository
	storage *storage.MinIO
	logger  *slog.Logger
}

func NewKbService(
	repo repository.Repository,
	s *storage.MinIO,
	logger *slog.Logger,
) *KbService {
	return &KbService{repo: repo, storage: s, logger: logger}
}

// --- KnowledgeBase ---

func (s *KbService) CreateKnowledgeBase(ctx context.Context, name, description string) (domain.KnowledgeBase, error) {
	uid, ok := jwtpkg.UserIDFromContext(ctx)
	if !ok {
		return domain.KnowledgeBase{}, domain.ErrPermissionDenied
	}

	exists, err := s.repo.KBNameExists(ctx, name)
	if err != nil {
		s.logger.ErrorContext(ctx, "check kb name", slog.Any("err", err))
		return domain.KnowledgeBase{}, err
	}
	if exists {
		return domain.KnowledgeBase{}, domain.ErrKBNameExists
	}

	id, err := s.repo.CreateKB(ctx, domain.NewKnowledgeBaseInput{
		Name:        name,
		Description: description,
		OwnerID:     uid,
	})
	if err != nil {
		s.logger.ErrorContext(ctx, "create kb", slog.Any("err", err))
		return domain.KnowledgeBase{}, err
	}

	return s.repo.FindKBByID(ctx, id)
}

func (s *KbService) ListKnowledgeBases(ctx context.Context) ([]domain.KnowledgeBase, error) {
	return s.repo.FindAllKB(ctx)
}

func (s *KbService) GetKnowledgeBase(ctx context.Context, id int64) (domain.KnowledgeBase, error) {
	return s.repo.FindKBByID(ctx, id)
}

func (s *KbService) UpdateKnowledgeBase(ctx context.Context, id int64, name, description string) (domain.KnowledgeBase, error) {
	kb, err := s.repo.FindKBByID(ctx, id)
	if err != nil {
		return domain.KnowledgeBase{}, err
	}
	if err := s.checkOwnerOrAdmin(ctx, kb.OwnerID); err != nil {
		return domain.KnowledgeBase{}, err
	}

	if name != kb.Name {
		exists, err := s.repo.KBNameExists(ctx, name)
		if err != nil {
			s.logger.ErrorContext(ctx, "check kb name", slog.Any("err", err))
			return domain.KnowledgeBase{}, err
		}
		if exists {
			return domain.KnowledgeBase{}, domain.ErrKBNameExists
		}
	}

	if err := s.repo.UpdateKB(ctx, domain.UpdateKnowledgeBaseInput{
		ID:          id,
		Name:        name,
		Description: description,
	}); err != nil {
		s.logger.ErrorContext(ctx, "update kb", slog.Any("err", err))
		return domain.KnowledgeBase{}, err
	}

	return s.repo.FindKBByID(ctx, id)
}

func (s *KbService) DeleteKnowledgeBase(ctx context.Context, id int64) error {
	kb, err := s.repo.FindKBByID(ctx, id)
	if err != nil {
		return err
	}
	if err := s.checkOwnerOrAdmin(ctx, kb.OwnerID); err != nil {
		return err
	}
	return s.repo.DeleteKB(ctx, id)
}

// --- Document ---

func (s *KbService) UploadDocument(ctx context.Context, kbID int64, filename, contentType string, data []byte) (domain.Document, error) {
	if _, err := s.repo.FindKBByID(ctx, kbID); err != nil {
		return domain.Document{}, err
	}

	if err := validateFile(filename, len(data)); err != nil {
		return domain.Document{}, err
	}

	ext := filepath.Ext(filename)
	objectKey := fmt.Sprintf("%d/%s%s", kbID, uuid.New().String(), ext)

	docID, err := s.repo.CreateDocument(ctx, domain.NewDocumentInput{
		KBID:        kbID,
		Filename:    filename,
		ObjectKey:   objectKey,
		ContentType: contentType,
		FileSize:    int32(len(data)),
	})
	if err != nil {
		s.logger.ErrorContext(ctx, "create document record", slog.Any("err", err))
		return domain.Document{}, err
	}

	if err := s.storage.Upload(ctx, objectKey, bytes.NewReader(data), int64(len(data)), contentType); err != nil {
		s.logger.ErrorContext(ctx, "upload to minio", slog.Any("err", err))
		_ = s.repo.UpdateDocumentStatus(ctx, docID, "error")
		return domain.Document{}, domain.ErrUploadFailed
	}

	if err := s.repo.UpdateDocumentStatus(ctx, docID, "ready"); err != nil {
		s.logger.ErrorContext(ctx, "update document status", slog.Any("err", err))
		return domain.Document{}, err
	}

	return s.repo.FindDocumentByID(ctx, kbID, docID)
}

func (s *KbService) ListDocuments(ctx context.Context, kbID int64) ([]domain.Document, error) {
	return s.repo.FindAllDocuments(ctx, kbID)
}

func (s *KbService) DeleteDocument(ctx context.Context, kbID, docID int64) error {
	doc, err := s.repo.FindDocumentByID(ctx, kbID, docID)
	if err != nil {
		return err
	}

	kb, err := s.repo.FindKBByID(ctx, kbID)
	if err != nil {
		return err
	}
	if err := s.checkOwnerOrAdmin(ctx, kb.OwnerID); err != nil {
		return err
	}

	if err := s.storage.Delete(ctx, doc.ObjectKey); err != nil {
		s.logger.ErrorContext(ctx, "delete from minio", slog.Any("err", err))
	}

	if err := s.repo.DeleteChunksByDocument(ctx, kbID, docID); err != nil {
		s.logger.ErrorContext(ctx, "delete chunks from milvus", slog.Any("err", err))
	}

	if err := s.repo.DeleteParseTasks(ctx, kbID, docID); err != nil {
		s.logger.ErrorContext(ctx, "delete parse tasks", slog.Any("err", err))
	}

	return s.repo.DeleteDocument(ctx, kbID, docID)
}

func (s *KbService) DownloadDocument(ctx context.Context, kbID, docID int64) (domain.Document, []byte, error) {
	doc, err := s.repo.FindDocumentByID(ctx, kbID, docID)
	if err != nil {
		return domain.Document{}, nil, err
	}

	reader, err := s.storage.Download(ctx, doc.ObjectKey)
	if err != nil {
		s.logger.ErrorContext(ctx, "download from minio", slog.Any("err", err))
		return domain.Document{}, nil, domain.ErrUploadFailed
	}
	defer reader.Close()

	data, err := io.ReadAll(reader)
	if err != nil {
		s.logger.ErrorContext(ctx, "read document data", slog.Any("err", err))
		return domain.Document{}, nil, domain.ErrUploadFailed
	}

	return doc, data, nil
}

// --- helpers ---

func (s *KbService) checkOwnerOrAdmin(ctx context.Context, ownerID int64) error {
	uid, ok := jwtpkg.UserIDFromContext(ctx)
	if !ok {
		return domain.ErrPermissionDenied
	}
	role, _ := jwtpkg.RoleFromContext(ctx)
	if role == "admin" || uid == ownerID {
		return nil
	}
	return domain.ErrPermissionDenied
}

func validateFile(filename string, size int) error {
	if size > maxFileSize {
		return domain.ErrFileTooLarge
	}
	ext := strings.ToLower(filepath.Ext(filename))
	if _, ok := allowedExtensions[ext]; !ok {
		return domain.ErrInvalidFileType
	}
	return nil
}

// --- Presigned URL ---

func (s *KbService) PrepareDocumentUpload(ctx context.Context, kbID int64, filename, contentType string, fileSize int64) (string, string, error) {
	if _, err := s.repo.FindKBByID(ctx, kbID); err != nil {
		return "", "", err
	}

	if err := validateFile(filename, int(fileSize)); err != nil {
		return "", "", err
	}

	ext := filepath.Ext(filename)
	objectKey := fmt.Sprintf("%d/%s%s", kbID, uuid.New().String(), ext)

	uploadURL, err := s.storage.PresignedPutObject(ctx, objectKey, presignedPutTTL)
	if err != nil {
		s.logger.ErrorContext(ctx, "presigned put url", slog.Any("err", err))
		return "", "", err
	}

	return objectKey, uploadURL, nil
}

func (s *KbService) ConfirmDocumentUpload(ctx context.Context, kbID int64, objectKey, filename, contentType string, fileSize int64) (domain.Document, error) {
	exists, err := s.storage.ObjectExists(ctx, objectKey)
	if err != nil {
		s.logger.ErrorContext(ctx, "check object exists", slog.Any("err", err))
		return domain.Document{}, err
	}
	if !exists {
		return domain.Document{}, domain.ErrUploadNotConfirmed
	}

	docID, err := s.repo.CreateDocument(ctx, domain.NewDocumentInput{
		KBID:        kbID,
		Filename:    filename,
		ObjectKey:   objectKey,
		ContentType: contentType,
		FileSize:    int32(fileSize),
	})
	if err != nil {
		s.logger.ErrorContext(ctx, "create document record", slog.Any("err", err))
		return domain.Document{}, err
	}

	if err := s.repo.UpdateDocumentStatus(ctx, docID, "ready"); err != nil {
		s.logger.ErrorContext(ctx, "update document status", slog.Any("err", err))
		return domain.Document{}, err
	}

	return s.repo.FindDocumentByID(ctx, kbID, docID)
}
func (s *KbService) GetDocumentDownloadURL(ctx context.Context, kbID, docID int64) (string, domain.Document, error) {
	doc, err := s.repo.FindDocumentByID(ctx, kbID, docID)
	if err != nil {
		return "", domain.Document{}, err
	}

	if doc.Status != "ready" {
		return "", domain.Document{}, domain.ErrUploadNotConfirmed
	}

	url, err := s.storage.PresignedGetObject(ctx, doc.ObjectKey, presignedGetTTL)
	if err != nil {
		s.logger.ErrorContext(ctx, "presigned get url", slog.Any("err", err))
		return "", domain.Document{}, err
	}

	return url, doc, nil
}

// --- Chunk & Parse ---

func (s *KbService) ListChunks(ctx context.Context, kbID, docID int64) ([]domain.Chunk, error) {
	return s.repo.FindChunksByDocument(ctx, kbID, docID)
}

func (s *KbService) DeleteChunk(ctx context.Context, kbID, docID int64, chunkIndex int32) error {
	return s.repo.DeleteChunk(ctx, kbID, docID, chunkIndex)
}

func (s *KbService) GetParseStatus(ctx context.Context, kbID, docID int64) (domain.Document, error) {
	return s.repo.FindDocumentByID(ctx, kbID, docID)
}
