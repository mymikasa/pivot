package dao

import (
	"context"
	"time"
)

type DocumentChunk struct {
	ID           int64  `gorm:"primaryKey;autoIncrement"`
	KBID         int64  `gorm:"not null;index:idx_document_chunks_kb_document"`
	DocumentID   int64  `gorm:"not null;index:idx_document_chunks_kb_document"`
	ChunkIndex   int32  `gorm:"not null"`
	Content      string `gorm:"type:text;not null"`
	TokenCount   int32  `gorm:"not null;default:0"`
	SourcePage   *int32
	SectionTitle string `gorm:"size:512"`
	SectionPath  string `gorm:"size:1024"`
	Filename     string `gorm:"size:255;not null"`
	ContentType  string `gorm:"size:100;not null"`
	ChunkSize    int32  `gorm:"not null;default:512"`
	ChunkOverlap int32  `gorm:"not null;default:50"`
	Version      int32  `gorm:"not null;default:1"`
	UserID       *int64
	MilvusID     *int64 `gorm:"index"`
	CreatedAt    time.Time
	UpdatedAt    time.Time
}

func (DocumentChunk) TableName() string { return "document_chunks" }

func (d *KbDAO) FindChunksByDocument(ctx context.Context, kbID, docID int64) ([]DocumentChunk, error) {
	var rows []DocumentChunk
	err := d.db.WithContext(ctx).
		Where("kb_id = ? AND document_id = ?", kbID, docID).
		Order("chunk_index ASC").
		Find(&rows).Error
	if err != nil {
		return nil, err
	}
	return rows, nil
}

func (d *KbDAO) DeleteChunksByDocument(ctx context.Context, kbID, docID int64) error {
	return d.db.WithContext(ctx).
		Where("kb_id = ? AND document_id = ?", kbID, docID).
		Delete(&DocumentChunk{}).Error
}

func (d *KbDAO) DeleteChunk(ctx context.Context, kbID, docID int64, chunkIndex int32) error {
	return d.db.WithContext(ctx).
		Where("kb_id = ? AND document_id = ? AND chunk_index = ?", kbID, docID, chunkIndex).
		Delete(&DocumentChunk{}).Error
}
