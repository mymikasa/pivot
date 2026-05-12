//go:build wireinject

package main

import (
	"github.com/google/wire"

	"github.com/mymikasa/pivot/app/kb/ioc"
)

func initApp() (*ioc.App, func(), error) {
	wire.Build(ioc.ProviderSet, ioc.NewApp)
	return nil, nil, nil
}
