package repository

import (
	"context"

	"github.com/mymikasa/pivot/app/kb/domain"
	"github.com/mymikasa/pivot/app/kb/repository/dao"
)

// --- Document ---

func (r *KbRepository) FindAllDocuments(ctx context.Context, kbID int64) ([]domain.Document, error) {
	rows, err := r.dao.FindAllDocuments(ctx, kbID)
	if err != nil {
		return nil, err
	}
	items := make([]domain.Document, 0, len(rows))
	for _, row := range rows {
		items = append(items, toDomainDocument(row))
	}
	return items, nil
}

func (r *KbRepository) FindDocumentByID(ctx context.Context, kbID, docID int64) (domain.Document, error) {
	row, err := r.dao.FindDocumentByID(ctx, kbID, docID)
	if err != nil {
		return domain.Document{}, err
	}
	return toDomainDocument(row), nil
}

func (r *KbRepository) CreateDocument(ctx context.Context, in domain.NewDocumentInput) (int64, error) {
	return r.dao.CreateDocument(ctx, dao.Document{
		KBID:        in.KBID,
		Filename:    in.Filename,
		ObjectKey:   in.ObjectKey,
		ContentType: in.ContentType,
		FileSize:    in.FileSize,
		Status:      "uploading",
	})
}

func (r *KbRepository) UpdateDocumentStatus(ctx context.Context, id int64, status string) error {
	return r.dao.UpdateDocumentStatus(ctx, id, status)
}

func (r *KbRepository) UpdateDocumentParseState(ctx context.Context, docID int64, status string, taskID *int64, progress int32, parseErr string) error {
	return r.dao.UpdateDocumentParseState(ctx, docID, status, taskID, progress, parseErr)
}

func (r *KbRepository) DeleteDocument(ctx context.Context, kbID, docID int64) error {
	return r.dao.DeleteDocument(ctx, kbID, docID)
}

func toDomainDocument(d dao.Document) domain.Document {
	return domain.Document{
		ID:            d.ID,
		KBID:          d.KBID,
		Filename:      d.Filename,
		ObjectKey:     d.ObjectKey,
		ContentType:   d.ContentType,
		FileSize:      d.FileSize,
		Status:        d.Status,
		ParseStatus:   d.ParseStatus,
		ParseTaskID:   d.ParseTaskID,
		ParseProgress: d.ParseProgress,
		ParseError:    d.ParseError,
		ParsedAt:      d.ParsedAt,
		CreatedAt:     d.CreatedAt,
	}
}
