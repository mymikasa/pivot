package service

import (
	"context"
	"errors"
	"log/slog"

	"golang.org/x/crypto/bcrypt"

	"github.com/mymikasa/pivot/app/user/domain"
	"github.com/mymikasa/pivot/app/user/repository"
	jwtpkg "github.com/mymikasa/pivot/pkg/jwt"
)

type UserService struct {
	repo     repository.Repository
	issuer   *jwtpkg.Issuer
	verifier *jwtpkg.Verifier
	logger   *slog.Logger
}

func NewUserService(
	repo repository.Repository,
	issuer *jwtpkg.Issuer,
	verifier *jwtpkg.Verifier,
	logger *slog.Logger,
) *UserService {
	return &UserService{repo: repo, issuer: issuer, verifier: verifier, logger: logger}
}

func (s *UserService) Login(ctx context.Context, username, password string) (string, string, error) {
	u, err := s.repo.FindByUsername(ctx, username)
	if err != nil {
		if errors.Is(err, domain.ErrUserNotFound) {
			return "", "", domain.ErrInvalidCredentials
		}
		s.logger.ErrorContext(ctx, "lookup user", slog.Any("err", err))
		return "", "", err
	}
	if !u.IsActive {
		return "", "", domain.ErrUserInactive
	}
	if err := bcrypt.CompareHashAndPassword([]byte(u.HashedPassword), []byte(password)); err != nil {
		return "", "", domain.ErrInvalidCredentials
	}
	access, refresh, err := s.issuer.Sign(u.ID, "")
	if err != nil {
		s.logger.ErrorContext(ctx, "sign tokens", slog.Any("err", err))
		return "", "", err
	}
	return access, refresh, nil
}

func (s *UserService) Logout(ctx context.Context) error {
	if uid, ok := jwtpkg.UserIDFromContext(ctx); ok {
		s.logger.InfoContext(ctx, "user logout", slog.Int64("user_id", uid))
	}
	return nil
}

func (s *UserService) RefreshToken(ctx context.Context, refreshToken string) (string, error) {
	claims, err := s.verifier.Parse(refreshToken)
	if err != nil {
		return "", domain.ErrUnauthenticated
	}
	if claims.Type != jwtpkg.RefreshToken {
		return "", domain.ErrUnauthenticated
	}
	access, err := s.issuer.Refresh(claims)
	if err != nil {
		s.logger.ErrorContext(ctx, "refresh token", slog.Any("err", err))
		return "", err
	}
	return access, nil
}

func (s *UserService) GetAllUser(ctx context.Context) ([]domain.User, error) {
	users, err := s.repo.FindAll(ctx)
	if err != nil {
		s.logger.ErrorContext(ctx, "find all users", slog.Any("err", err))
		return nil, err
	}
	return users, nil
}
