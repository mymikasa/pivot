package service

import (
	"context"

	"github.com/mymikasa/pivot/app/kb/domain"
)

type Service interface {
	// KnowledgeBase
	CreateKnowledgeBase(ctx context.Context, name, description string) (domain.KnowledgeBase, error)
	ListKnowledgeBases(ctx context.Context) ([]domain.KnowledgeBase, error)
	GetKnowledgeBase(ctx context.Context, id int64) (domain.KnowledgeBase, error)
	UpdateKnowledgeBase(ctx context.Context, id int64, name, description string) (domain.KnowledgeBase, error)
	DeleteKnowledgeBase(ctx context.Context, id int64) error

	// Document
	UploadDocument(ctx context.Context, kbID int64, filename, contentType string, data []byte) (domain.Document, error)
	ListDocuments(ctx context.Context, kbID int64) ([]domain.Document, error)
	DeleteDocument(ctx context.Context, kbID, docID int64) error
	DownloadDocument(ctx context.Context, kbID, docID int64) (domain.Document, []byte, error)

	// Presigned URL
	PrepareDocumentUpload(ctx context.Context, kbID int64, filename, contentType string, fileSize int64) (objectKey string, uploadURL string, err error)
	ConfirmDocumentUpload(ctx context.Context, kbID int64, objectKey, filename, contentType string, fileSize int64) (domain.Document, error)
	GetDocumentDownloadURL(ctx context.Context, kbID, docID int64) (string, domain.Document, error)

	// Chunk & Parse
	ListChunks(ctx context.Context, kbID, docID int64) ([]domain.Chunk, error)
	GetParseStatus(ctx context.Context, kbID, docID int64) (domain.Document, error)
}
