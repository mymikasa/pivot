package domain

import "time"

type User struct {
	ID             int64
	Username       string
	Email          string
	HashedPassword string
	Role           string
	IsActive       bool
	CreatedAt      time.Time
}

type NewUserInput struct {
	Username       string
	Email          string
	HashedPassword string
	RoleID         int64
}
