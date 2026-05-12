//go:build wireinject

package main

import (
	"github.com/google/wire"

	"github.com/mymikasa/pivot/app/user/ioc"
)

func initApp() (*ioc.App, func(), error) {
	wire.Build(ioc.ProviderSet, ioc.NewApp)
	return nil, nil, nil
}
