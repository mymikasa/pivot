package domain

import "time"

type User struct {
	ID             int64
	Username       string
	Email          string
	HashedPassword string
	IsActive       bool
	CreatedAt      time.Time
}
