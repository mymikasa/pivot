package domain

import "time"

type KnowledgeBase struct {
	ID            int64
	Name          string
	Description   string
	OwnerID       int64
	DocumentCount int32
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

type NewKnowledgeBaseInput struct {
	Name        string
	Description string
	OwnerID     int64
}

type UpdateKnowledgeBaseInput struct {
	ID          int64
	Name        string
	Description string
}
