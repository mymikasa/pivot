package jwt

import "time"

type Config struct {
	Secret     string        `mapstructure:"secret"`
	AccessTTL  time.Duration `mapstructure:"access_ttl"`
	RefreshTTL time.Duration `mapstructure:"refresh_ttl"`
	Issuer     string        `mapstructure:"issuer"`
	Audience   string        `mapstructure:"audience"`
}
