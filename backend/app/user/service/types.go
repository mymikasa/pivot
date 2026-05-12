package service

import (
	"context"

	"github.com/mymikasa/pivot/app/user/domain"
)

type Service interface {
	Register(ctx context.Context, username, email, password string) error
	Login(ctx context.Context, username, password string) (access, refresh string, user domain.User, err error)
	Logout(ctx context.Context) error
	RefreshToken(ctx context.Context, refreshToken string) (access string, err error)
	GetCurrentUser(ctx context.Context) (domain.User, error)
	GetAllUser(ctx context.Context) ([]domain.User, error)
}
