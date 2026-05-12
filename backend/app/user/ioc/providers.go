package ioc

import (
	"github.com/google/wire"

	usergrpc "github.com/mymikasa/pivot/app/user/grpc"
	"github.com/mymikasa/pivot/app/user/repository"
	"github.com/mymikasa/pivot/app/user/repository/dao"
	"github.com/mymikasa/pivot/app/user/service"
)

var ProviderSet = wire.NewSet(
	InitConfig,
	InitDB,
	InitLogger,
	InitJWTIssuer,
	InitJWTVerifier,
	InitGRPCServer,
	InitHTTPGateway,
	dao.NewUserDAO,
	repository.NewUserRepository,
	service.NewUserService,
	usergrpc.NewUserServer,
	wire.Bind(new(dao.DAO), new(*dao.UserDAO)),
	wire.Bind(new(repository.Repository), new(*repository.UserRepository)),
	wire.Bind(new(service.Service), new(*service.UserService)),
)
