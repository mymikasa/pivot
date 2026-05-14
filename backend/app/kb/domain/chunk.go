package domain

type Chunk struct {
	ID         int64
	KBID       int64
	DocumentID int64
	ChunkIndex int32
	Content    string
	TokenCount int32
}
