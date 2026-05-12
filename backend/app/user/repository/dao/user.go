package dao

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"

	"github.com/mymikasa/pivot/app/user/domain"
)

type User struct {
	ID             int64  `gorm:"primaryKey;autoIncrement"`
	Username       string `gorm:"size:64;uniqueIndex;not null"`
	Email          string `gorm:"size:255;uniqueIndex;not null"`
	HashedPassword string `gorm:"size:255;not null"`
	RoleID         int64  `gorm:"not null"`
	IsActive       bool   `gorm:"not null;default:true"`
	CreatedAt      time.Time
	UpdatedAt      time.Time
}

func (User) TableName() string { return "users" }

type UserDAO struct {
	db *gorm.DB
}

func NewUserDAO(db *gorm.DB) *UserDAO {
	return &UserDAO{db: db}
}

func (d *UserDAO) FindAll(ctx context.Context) ([]User, error) {
	var users []User
	if err := d.db.WithContext(ctx).Find(&users).Error; err != nil {
		return nil, err
	}
	return users, nil
}

func (d *UserDAO) FindByUsername(ctx context.Context, username string) (User, error) {
	var u User
	err := d.db.WithContext(ctx).Where("username = ?", username).First(&u).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return User{}, domain.ErrUserNotFound
		}
		return User{}, err
	}
	return u, nil
}
