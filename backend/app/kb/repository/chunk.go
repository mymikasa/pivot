package repository

import (
	"context"
	"fmt"

	"github.com/milvus-io/milvus-sdk-go/v2/client"

	"github.com/mymikasa/pivot/app/kb/domain"
	"github.com/mymikasa/pivot/app/kb/repository/dao"
)

type ChunkRepository struct {
	dao            dao.DAO
	milvus         client.Client
	collectionName string
}

func NewChunkRepository(d dao.DAO, milvus client.Client, collectionName string) *ChunkRepository {
	return &ChunkRepository{dao: d, milvus: milvus, collectionName: collectionName}
}

func (r *ChunkRepository) FindChunksByDocument(ctx context.Context, kbID, docID int64) ([]domain.Chunk, error) {
	rows, err := r.dao.FindChunksByDocument(ctx, kbID, docID)
	if err != nil {
		return nil, fmt.Errorf("find document chunks: %w", err)
	}

	chunks := make([]domain.Chunk, 0, len(rows))
	for _, row := range rows {
		chunks = append(chunks, domain.Chunk{
			ID:           row.ID,
			KBID:         row.KBID,
			DocumentID:   row.DocumentID,
			ChunkIndex:   row.ChunkIndex,
			Content:      row.Content,
			TokenCount:   row.TokenCount,
			SourcePage:   row.SourcePage,
			SectionTitle: row.SectionTitle,
			SectionPath:  row.SectionPath,
			Filename:     row.Filename,
			ContentType:  row.ContentType,
			ChunkSize:    row.ChunkSize,
			ChunkOverlap: row.ChunkOverlap,
			Version:      row.Version,
			UserID:       row.UserID,
			MilvusID:     row.MilvusID,
			CreatedAt:    row.CreatedAt,
			UpdatedAt:    row.UpdatedAt,
		})
	}

	return chunks, nil
}

func (r *ChunkRepository) DeleteChunksByDocument(ctx context.Context, kbID, docID int64) error {
	expr := fmt.Sprintf(`kb_id == %d and document_id == %d`, kbID, docID)
	if err := r.milvus.Delete(ctx, r.collectionName, "", expr); err != nil {
		return fmt.Errorf("milvus delete chunks: %w", err)
	}
	if err := r.dao.DeleteChunksByDocument(ctx, kbID, docID); err != nil {
		return fmt.Errorf("delete document chunks: %w", err)
	}
	return nil
}

func (r *ChunkRepository) DeleteChunk(ctx context.Context, kbID, docID int64, chunkIndex int32) error {
	expr := fmt.Sprintf(`kb_id == %d and document_id == %d and chunk_index == %d`, kbID, docID, chunkIndex)
	if err := r.milvus.Delete(ctx, r.collectionName, "", expr); err != nil {
		return fmt.Errorf("milvus delete chunk: %w", err)
	}
	if err := r.dao.DeleteChunk(ctx, kbID, docID, chunkIndex); err != nil {
		return fmt.Errorf("delete document chunk: %w", err)
	}
	return nil
}
