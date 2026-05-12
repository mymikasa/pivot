package ioc

import (
	"github.com/mymikasa/pivot/pkg/storage"
)

func InitMinIO(c *Config) (*storage.MinIO, error) {
	return storage.NewMinIO(c.MinIO)
}
