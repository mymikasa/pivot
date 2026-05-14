package ioc

import (
	"github.com/google/wire"

	kbgrpc "github.com/mymikasa/pivot/app/kb/grpc"
	"github.com/mymikasa/pivot/app/kb/repository"
	"github.com/mymikasa/pivot/app/kb/repository/dao"
	"github.com/mymikasa/pivot/app/kb/service"
)

var ProviderSet = wire.NewSet(
	InitConfig,
	InitDB,
	InitLogger,
	InitJWTIssuer,
	InitJWTVerifier,
	InitMinIO,
	InitMilvus,
	InitMilvusCollectionName,
	InitGRPCServer,
	InitHTTPGateway,
	dao.NewKbDAO,
	repository.NewChunkRepository,
	repository.NewKbRepository,
	service.NewKbService,
	kbgrpc.NewKbServer,
	wire.Bind(new(dao.DAO), new(*dao.KbDAO)),
	wire.Bind(new(repository.Repository), new(*repository.KbRepository)),
	wire.Bind(new(service.Service), new(*service.KbService)),
)
