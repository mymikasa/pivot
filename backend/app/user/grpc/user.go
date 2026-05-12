package grpc

import (
	"context"

	"google.golang.org/protobuf/types/known/timestamppb"

	userv1 "github.com/mymikasa/pivot/api/gen/user/v1"
	"github.com/mymikasa/pivot/app/user/domain"
	"github.com/mymikasa/pivot/app/user/service"
)

const tokenTypeBearer = "Bearer"

type UserServer struct {
	userv1.UnimplementedUserServiceServer
	svc service.Service
}

func NewUserServer(svc service.Service) *UserServer {
	return &UserServer{svc: svc}
}

func (g *UserServer) Register(ctx context.Context, req *userv1.RegisterRequest) (*userv1.RegisterResponse, error) {
	if err := g.svc.Register(ctx, req.GetUsername(), req.GetEmail(), req.GetPassword()); err != nil {
		return nil, toGRPCError(err)
	}
	return &userv1.RegisterResponse{Message: "registered"}, nil
}

func (g *UserServer) Login(ctx context.Context, req *userv1.LoginRequest) (*userv1.LoginResponse, error) {
	access, refresh, user, err := g.svc.Login(ctx, req.GetUsername(), req.GetPassword())
	if err != nil {
		return nil, toGRPCError(err)
	}
	return &userv1.LoginResponse{
		AccessToken:  access,
		RefreshToken: refresh,
		TokenType:    tokenTypeBearer,
		User:         toProto(user),
	}, nil
}

func (g *UserServer) Logout(ctx context.Context, _ *userv1.LogoutRequest) (*userv1.LogoutResponse, error) {
	if err := g.svc.Logout(ctx); err != nil {
		return nil, toGRPCError(err)
	}
	return &userv1.LogoutResponse{}, nil
}

func (g *UserServer) RefreshToken(ctx context.Context, req *userv1.RefreshTokenRequest) (*userv1.RefreshTokenResponse, error) {
	access, err := g.svc.RefreshToken(ctx, req.GetRefreshToken())
	if err != nil {
		return nil, toGRPCError(err)
	}
	return &userv1.RefreshTokenResponse{AccessToken: access}, nil
}

func (g *UserServer) GetCurrentUser(ctx context.Context, _ *userv1.GetCurrentUserRequest) (*userv1.GetCurrentUserResponse, error) {
	user, err := g.svc.GetCurrentUser(ctx)
	if err != nil {
		return nil, toGRPCError(err)
	}
	return &userv1.GetCurrentUserResponse{User: toProto(user)}, nil
}

func (g *UserServer) GetAllUser(ctx context.Context, _ *userv1.GetAllUserRequest) (*userv1.GetAllUserResponse, error) {
	users, err := g.svc.GetAllUser(ctx)
	if err != nil {
		return nil, toGRPCError(err)
	}
	pb := make([]*userv1.User, 0, len(users))
	for _, u := range users {
		pb = append(pb, toProto(u))
	}
	return &userv1.GetAllUserResponse{Users: pb}, nil
}

func toProto(u domain.User) *userv1.User {
	return &userv1.User{
		Id:        u.ID,
		Username:  u.Username,
		Email:     u.Email,
		IsActive:  u.IsActive,
		CreatedAt: timestamppb.New(u.CreatedAt),
		Role:      u.Role,
	}
}
