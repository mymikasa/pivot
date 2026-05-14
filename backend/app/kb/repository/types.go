package repository

import (
	"context"

	"github.com/mymikasa/pivot/app/kb/domain"
)

type Repository interface {
	// KnowledgeBase
	FindAllKB(ctx context.Context) ([]domain.KnowledgeBase, error)
	FindKBByID(ctx context.Context, id int64) (domain.KnowledgeBase, error)
	CreateKB(ctx context.Context, in domain.NewKnowledgeBaseInput) (int64, error)
	UpdateKB(ctx context.Context, in domain.UpdateKnowledgeBaseInput) error
	DeleteKB(ctx context.Context, id int64) error
	KBNameExists(ctx context.Context, name string) (bool, error)

	// Document
	FindAllDocuments(ctx context.Context, kbID int64) ([]domain.Document, error)
	FindDocumentByID(ctx context.Context, kbID, docID int64) (domain.Document, error)
	CreateDocument(ctx context.Context, in domain.NewDocumentInput) (int64, error)
	UpdateDocumentStatus(ctx context.Context, id int64, status string) error
	UpdateDocumentParseState(ctx context.Context, docID int64, status string, taskID *int64, progress int32, parseErr string) error
	DeleteDocument(ctx context.Context, kbID, docID int64) error

	// Chunk
	FindChunksByDocument(ctx context.Context, kbID, docID int64) ([]domain.Chunk, error)
	DeleteChunksByDocument(ctx context.Context, kbID, docID int64) error
}
