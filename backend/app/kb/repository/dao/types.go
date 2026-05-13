package dao

import "context"

type DAO interface {
	// KnowledgeBase
	FindAllKB(ctx context.Context) ([]KnowledgeBase, error)
	FindKBByID(ctx context.Context, id int64) (KnowledgeBase, error)
	FindKBByName(ctx context.Context, name string) (KnowledgeBase, error)
	CreateKB(ctx context.Context, kb KnowledgeBase) (int64, error)
	UpdateKB(ctx context.Context, kb KnowledgeBase) error
	DeleteKB(ctx context.Context, id int64) error
	CountDocumentsByKB(ctx context.Context, kbID int64) (int32, error)

	// Document
	FindAllDocuments(ctx context.Context, kbID int64) ([]Document, error)
	FindDocumentByID(ctx context.Context, kbID, docID int64) (Document, error)
	CreateDocument(ctx context.Context, doc Document) (int64, error)
	UpdateDocumentStatus(ctx context.Context, id int64, status string) error
	UpdateDocumentParseState(ctx context.Context, docID int64, status string, taskID *int64, progress int32, parseErr string) error
	DeleteDocument(ctx context.Context, kbID, docID int64) error
}
