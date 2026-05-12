package dao

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"

	"github.com/mymikasa/pivot/app/kb/domain"
)

type KnowledgeBase struct {
	ID          int64  `gorm:"primaryKey;autoIncrement"`
	Name        string `gorm:"size:128;uniqueIndex;not null"`
	Description string `gorm:"type:text"`
	OwnerID     int64  `gorm:"not null;index"`
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

func (KnowledgeBase) TableName() string { return "knowledge_bases" }

type KbDAO struct {
	db *gorm.DB
}

func NewKbDAO(db *gorm.DB) *KbDAO {
	return &KbDAO{db: db}
}

func (d *KbDAO) FindAllKB(ctx context.Context) ([]KnowledgeBase, error) {
	var rows []KnowledgeBase
	if err := d.db.WithContext(ctx).Order("id DESC").Find(&rows).Error; err != nil {
		return nil, err
	}
	return rows, nil
}

func (d *KbDAO) FindKBByID(ctx context.Context, id int64) (KnowledgeBase, error) {
	var row KnowledgeBase
	err := d.db.WithContext(ctx).Where("id = ?", id).First(&row).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return KnowledgeBase{}, domain.ErrKBNotFound
		}
		return KnowledgeBase{}, err
	}
	return row, nil
}

func (d *KbDAO) FindKBByName(ctx context.Context, name string) (KnowledgeBase, error) {
	var row KnowledgeBase
	err := d.db.WithContext(ctx).Where("name = ?", name).First(&row).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return KnowledgeBase{}, domain.ErrKBNotFound
		}
		return KnowledgeBase{}, err
	}
	return row, nil
}

func (d *KbDAO) CreateKB(ctx context.Context, kb KnowledgeBase) (int64, error) {
	if err := d.db.WithContext(ctx).Create(&kb).Error; err != nil {
		return 0, err
	}
	return kb.ID, nil
}

func (d *KbDAO) UpdateKB(ctx context.Context, kb KnowledgeBase) error {
	return d.db.WithContext(ctx).Model(&KnowledgeBase{}).
		Where("id = ?", kb.ID).
		Updates(map[string]any{
			"name":        kb.Name,
			"description": kb.Description,
		}).Error
}

func (d *KbDAO) DeleteKB(ctx context.Context, id int64) error {
	return d.db.WithContext(ctx).Where("id = ?", id).Delete(&KnowledgeBase{}).Error
}

func (d *KbDAO) CountDocumentsByKB(ctx context.Context, kbID int64) (int32, error) {
	var count int64
	err := d.db.WithContext(ctx).Model(&Document{}).Where("kb_id = ?", kbID).Count(&count).Error
	return int32(count), err
}
