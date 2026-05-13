package domain

import "time"

const (
	DocumentParseStatusNotParsed = "not_parsed"
	DocumentParseStatusPending   = "pending"
	DocumentParseStatusRunning   = "running"
	DocumentParseStatusCompleted = "completed"
	DocumentParseStatusFailed    = "failed"
)

type Document struct {
	ID            int64
	KBID          int64
	Filename      string
	ObjectKey     string
	ContentType   string
	FileSize      int32
	Status        string
	ParseStatus   string
	ParseTaskID   *int64
	ParseProgress int32
	ParseError    string
	ParsedAt      *time.Time
	CreatedAt     time.Time
}

type NewDocumentInput struct {
	KBID        int64
	Filename    string
	ObjectKey   string
	ContentType string
	FileSize    int32
}
