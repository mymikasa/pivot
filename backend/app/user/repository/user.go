package repository

import (
	"context"

	"github.com/mymikasa/pivot/app/user/domain"
	"github.com/mymikasa/pivot/app/user/repository/dao"
)

type UserRepository struct {
	dao dao.DAO
}

func NewUserRepository(d dao.DAO) *UserRepository {
	return &UserRepository{dao: d}
}

func (r *UserRepository) FindAll(ctx context.Context) ([]domain.User, error) {
	rows, err := r.dao.FindAll(ctx)
	if err != nil {
		return nil, err
	}
	users := make([]domain.User, 0, len(rows))
	for _, row := range rows {
		users = append(users, toDomain(row))
	}
	return users, nil
}

func (r *UserRepository) FindByUsername(ctx context.Context, username string) (domain.User, error) {
	row, err := r.dao.FindByUsername(ctx, username)
	if err != nil {
		return domain.User{}, err
	}
	return toDomain(row), nil
}

func toDomain(u dao.User) domain.User {
	return domain.User{
		ID:             u.ID,
		Username:       u.Username,
		Email:          u.Email,
		HashedPassword: u.HashedPassword,
		IsActive:       u.IsActive,
		CreatedAt:      u.CreatedAt,
	}
}
