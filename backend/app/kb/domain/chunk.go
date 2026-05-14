package domain

import "time"

type Chunk struct {
	ID           int64
	KBID         int64
	DocumentID   int64
	ChunkIndex   int32
	Content      string
	TokenCount   int32
	SourcePage   *int32
	SectionTitle string
	SectionPath  string
	Filename     string
	ContentType  string
	ChunkSize    int32
	ChunkOverlap int32
	Version      int32
	UserID       *int64
	MilvusID     *int64
	CreatedAt    time.Time
	UpdatedAt    time.Time
}
