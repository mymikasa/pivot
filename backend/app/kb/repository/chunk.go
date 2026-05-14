package repository

import (
	"context"
	"fmt"
	"strconv"

	"github.com/milvus-io/milvus-sdk-go/v2/client"
	"github.com/milvus-io/milvus-sdk-go/v2/entity"

	"github.com/mymikasa/pivot/app/kb/domain"
)

type ChunkRepository struct {
	milvus         client.Client
	collectionName string
}

func NewChunkRepository(milvus client.Client, collectionName string) *ChunkRepository {
	return &ChunkRepository{milvus: milvus, collectionName: collectionName}
}

func (r *ChunkRepository) FindChunksByDocument(ctx context.Context, kbID, docID int64) ([]domain.Chunk, error) {
	expr := fmt.Sprintf(`kb_id == "%d" and doc_document_id == "%d"`, kbID, docID)

	columns, err := r.milvus.Query(
		ctx,
		r.collectionName,
		nil,
		expr,
		[]string{"chunk_index", "text"},
	)
	if err != nil {
		return nil, fmt.Errorf("milvus query chunks: %w", err)
	}

	var chunkIndices []int64
	var contents []string

	for _, col := range columns {
		switch col.Name() {
		case "chunk_index":
			if v, ok := col.(*entity.ColumnInt64); ok {
				chunkIndices = v.Data()
			}
		case "text":
			if v, ok := col.(*entity.ColumnVarChar); ok {
				contents = v.Data()
			}
		}
	}

	rowCount := len(contents)
	chunks := make([]domain.Chunk, 0, rowCount)
	for i := 0; i < rowCount; i++ {
		c := domain.Chunk{
			KBID:       kbID,
			DocumentID: docID,
		}
		if i < len(chunkIndices) {
			c.ChunkIndex = int32(chunkIndices[i])
		}
		c.Content = contents[i]
		chunks = append(chunks, c)
	}

	return chunks, nil
}

func (r *ChunkRepository) DeleteChunksByDocument(ctx context.Context, kbID, docID int64) error {
	expr := fmt.Sprintf(`kb_id == "%d" and doc_document_id == "%d"`, kbID, docID)
	if err := r.milvus.Delete(ctx, r.collectionName, "", expr); err != nil {
		return fmt.Errorf("milvus delete chunks: %w", err)
	}
	return nil
}

func parseMetadataInt(m map[string]string, key string) int64 {
	if v, ok := m[key]; ok {
		n, _ := strconv.ParseInt(v, 10, 64)
		return n
	}
	return 0
}
