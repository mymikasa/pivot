package ioc

import (
	"context"

	"github.com/milvus-io/milvus-sdk-go/v2/client"
	"log/slog"
)

func InitMilvus(cfg *Config) (client.Client, func(), error) {
	c, err := client.NewClient(context.Background(), client.Config{
		Address: cfg.Milvus.URI,
	})
	if err != nil {
		return nil, nil, err
	}

	cleanup := func() {
		if err := c.Close(); err != nil {
			slog.Error("close milvus client", "err", err)
		}
	}
	return c, cleanup, nil
}

func InitMilvusCollectionName(cfg *Config) string {
	return cfg.Milvus.CollectionName
}
