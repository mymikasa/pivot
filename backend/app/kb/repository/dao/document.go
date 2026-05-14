package dao

import (
	"context"
	"errors"
	"time"

	"gorm.io/gorm"

	"github.com/mymikasa/pivot/app/kb/domain"
)

type Document struct {
	ID            int64  `gorm:"primaryKey;autoIncrement"`
	KBID          int64  `gorm:"not null;index"`
	Filename      string `gorm:"size:255;not null"`
	ObjectKey     string `gorm:"size:512;uniqueIndex;not null"`
	ContentType   string `gorm:"size:128;not null"`
	FileSize      int32  `gorm:"not null"`
	Status        string `gorm:"size:32;not null;default:uploading"`
	ParseStatus   string `gorm:"size:32;not null;default:not_parsed"`
	ParseTaskID   *int64 `gorm:"index"`
	ParseProgress int32  `gorm:"not null;default:0"`
	ParseError    string `gorm:"type:text"`
	ParsedAt      *time.Time
	CreatedAt     time.Time
}

func (Document) TableName() string { return "documents" }

func (d *KbDAO) FindAllDocuments(ctx context.Context, kbID int64) ([]Document, error) {
	var rows []Document
	err := d.db.WithContext(ctx).Where("kb_id = ?", kbID).Order("id DESC").Find(&rows).Error
	if err != nil {
		return nil, err
	}
	return rows, nil
}

func (d *KbDAO) FindDocumentByID(ctx context.Context, kbID, docID int64) (Document, error) {
	var row Document
	err := d.db.WithContext(ctx).Where("kb_id = ? AND id = ?", kbID, docID).First(&row).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return Document{}, domain.ErrDocNotFound
		}
		return Document{}, err
	}
	return row, nil
}

func (d *KbDAO) CreateDocument(ctx context.Context, doc Document) (int64, error) {
	if err := d.db.WithContext(ctx).Create(&doc).Error; err != nil {
		return 0, err
	}
	return doc.ID, nil
}

func (d *KbDAO) UpdateDocumentStatus(ctx context.Context, id int64, status string) error {
	return d.db.WithContext(ctx).Model(&Document{}).
		Where("id = ?", id).
		Update("status", status).Error
}

func (d *KbDAO) UpdateDocumentParseState(ctx context.Context, docID int64, status string, taskID *int64, progress int32, parseErr string) error {
	updates := map[string]any{
		"parse_status":   status,
		"parse_task_id":  taskID,
		"parse_progress": progress,
		"parse_error":    parseErr,
	}
	if status == domain.DocumentParseStatusCompleted {
		updates["parsed_at"] = time.Now()
	}
	return d.db.WithContext(ctx).Model(&Document{}).
		Where("id = ?", docID).
		Updates(updates).Error
}

func (d *KbDAO) DeleteDocument(ctx context.Context, kbID, docID int64) error {
	return d.db.WithContext(ctx).
		Where("kb_id = ? AND id = ?", kbID, docID).
		Delete(&Document{}).Error
}

func (d *KbDAO) DeleteParseTasks(ctx context.Context, kbID, docID int64) error {
	return d.db.WithContext(ctx).
		Exec("DELETE FROM parse_tasks WHERE kb_id = ? AND document_id = ?", kbID, docID).
		Error
}
