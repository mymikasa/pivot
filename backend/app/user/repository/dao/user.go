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
	// 联合查询填充，非数据库列
	RoleName string `gorm:"->;column:role_name"`
}

func (User) TableName() string { return "users" }

type Role struct {
	ID   int64
	Name string
}

func (Role) TableName() string { return "roles" }

type UserDAO struct {
	db *gorm.DB
}

func NewUserDAO(db *gorm.DB) *UserDAO {
	return &UserDAO{db: db}
}

// selectWithRole 提供 JOIN 查询的基础语句，把 roles.name 拼到 role_name 字段。
func (d *UserDAO) selectWithRole(ctx context.Context) *gorm.DB {
	return d.db.WithContext(ctx).
		Table("users").
		Select("users.*, roles.name AS role_name").
		Joins("LEFT JOIN roles ON roles.id = users.role_id")
}

func (d *UserDAO) FindAll(ctx context.Context) ([]User, error) {
	var users []User
	if err := d.selectWithRole(ctx).Scan(&users).Error; err != nil {
		return nil, err
	}
	return users, nil
}

func (d *UserDAO) FindByID(ctx context.Context, id int64) (User, error) {
	var u User
	err := d.selectWithRole(ctx).Where("users.id = ?", id).Scan(&u).Error
	if err != nil {
		return User{}, err
	}
	if u.ID == 0 {
		return User{}, domain.ErrUserNotFound
	}
	return u, nil
}

func (d *UserDAO) FindByUsername(ctx context.Context, username string) (User, error) {
	var u User
	err := d.selectWithRole(ctx).Where("users.username = ?", username).Scan(&u).Error
	if err != nil {
		return User{}, err
	}
	if u.ID == 0 {
		return User{}, domain.ErrUserNotFound
	}
	return u, nil
}

func (d *UserDAO) FindRoleIDByName(ctx context.Context, name string) (int64, error) {
	var r Role
	err := d.db.WithContext(ctx).Where("name = ?", name).First(&r).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return 0, domain.ErrRoleNotFound
		}
		return 0, err
	}
	return r.ID, nil
}

func (d *UserDAO) Create(ctx context.Context, u User) (int64, error) {
	if err := d.db.WithContext(ctx).Create(&u).Error; err != nil {
		return 0, err
	}
	return u.ID, nil
}

func (d *UserDAO) UsernameOrEmailExists(ctx context.Context, username, email string) (bool, error) {
	var count int64
	err := d.db.WithContext(ctx).
		Model(&User{}).
		Where("username = ? OR email = ?", username, email).
		Count(&count).Error
	if err != nil {
		return false, err
	}
	return count > 0, nil
}
