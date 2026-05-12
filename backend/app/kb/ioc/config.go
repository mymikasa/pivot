package ioc

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/viper"

	jwtpkg "github.com/mymikasa/pivot/pkg/jwt"
	"github.com/mymikasa/pivot/pkg/storage"
)

type Config struct {
	GRPC  GRPCConfig       `mapstructure:"grpc"`
	HTTP  HTTPConfig       `mapstructure:"http"`
	DB    DBConfig         `mapstructure:"db"`
	Log   LogConfig        `mapstructure:"log"`
	JWT   jwtpkg.Config    `mapstructure:"jwt"`
	MinIO storage.Config   `mapstructure:"minio"`
}

type GRPCConfig struct {
	Addr string `mapstructure:"addr"`
}

type HTTPConfig struct {
	Addr string `mapstructure:"addr"`
}

type DBConfig struct {
	DSN string `mapstructure:"dsn"`
}

type LogConfig struct {
	Level string `mapstructure:"level"`
}

func InitConfig() (*Config, error) {
	path := os.Getenv("PIVOT_KB_CONFIG")
	if path == "" {
		path = "./config.yaml"
	}

	v := viper.New()
	v.SetConfigFile(path)
	v.SetEnvPrefix("PIVOT_KB")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	for _, key := range []string{
		"jwt.secret", "db.dsn",
		"minio.access_key", "minio.secret_key",
	} {
		if err := v.BindEnv(key); err != nil {
			return nil, fmt.Errorf("bind env for %s: %w", key, err)
		}
	}

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("read config %s: %w", path, err)
	}

	var c Config
	if err := v.Unmarshal(&c); err != nil {
		return nil, fmt.Errorf("unmarshal config: %w", err)
	}
	if err := validate(&c); err != nil {
		return nil, err
	}
	return &c, nil
}

func validate(c *Config) error {
	if c.GRPC.Addr == "" {
		return fmt.Errorf("grpc.addr is required")
	}
	if c.HTTP.Addr == "" {
		return fmt.Errorf("http.addr is required")
	}
	if c.DB.DSN == "" {
		return fmt.Errorf("db.dsn is required")
	}
	if len(c.JWT.Secret) < 32 {
		return fmt.Errorf("jwt.secret must be at least 32 bytes; set PIVOT_KB_JWT_SECRET")
	}
	if c.JWT.AccessTTL <= 0 {
		return fmt.Errorf("jwt.access_ttl is required")
	}
	if c.JWT.RefreshTTL <= 0 {
		return fmt.Errorf("jwt.refresh_ttl is required")
	}
	if c.MinIO.Endpoint == "" {
		return fmt.Errorf("minio.endpoint is required")
	}
	return nil
}
