package ioc

import (
	"fmt"

	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func InitDB(c *Config) (*gorm.DB, func(), error) {
	db, err := gorm.Open(mysql.Open(c.DB.DSN), &gorm.Config{})
	if err != nil {
		return nil, nil, fmt.Errorf("open db: %w", err)
	}
	sqlDB, err := db.DB()
	if err != nil {
		return nil, nil, fmt.Errorf("get sql db: %w", err)
	}
	cleanup := func() { _ = sqlDB.Close() }
	return db, cleanup, nil
}
