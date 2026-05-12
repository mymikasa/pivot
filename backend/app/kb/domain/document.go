package domain

import "time"

type Document struct {
	ID          int64
	KBID        int64
	Filename    string
	ObjectKey   string
	ContentType string
	FileSize    int32
	Status      string
	CreatedAt   time.Time
}

type NewDocumentInput struct {
	KBID        int64
	Filename    string
	ObjectKey   string
	ContentType string
	FileSize    int32
}
