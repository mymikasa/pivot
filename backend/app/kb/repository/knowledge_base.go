package repository

import (
	"context"

	"github.com/mymikasa/pivot/app/kb/domain"
	"github.com/mymikasa/pivot/app/kb/repository/dao"
)

type KbRepository struct {
	dao dao.DAO
}

func NewKbRepository(d dao.DAO) *KbRepository {
	return &KbRepository{dao: d}
}

// --- KnowledgeBase ---

func (r *KbRepository) FindAllKB(ctx context.Context) ([]domain.KnowledgeBase, error) {
	rows, err := r.dao.FindAllKB(ctx)
	if err != nil {
		return nil, err
	}
	items := make([]domain.KnowledgeBase, 0, len(rows))
	for _, row := range rows {
		items = append(items, toDomainKB(row))
	}
	return items, nil
}

func (r *KbRepository) FindKBByID(ctx context.Context, id int64) (domain.KnowledgeBase, error) {
	row, err := r.dao.FindKBByID(ctx, id)
	if err != nil {
		return domain.KnowledgeBase{}, err
	}
	count, _ := r.dao.CountDocumentsByKB(ctx, id)
	kb := toDomainKB(row)
	kb.DocumentCount = count
	return kb, nil
}

func (r *KbRepository) CreateKB(ctx context.Context, in domain.NewKnowledgeBaseInput) (int64, error) {
	return r.dao.CreateKB(ctx, dao.KnowledgeBase{
		Name:        in.Name,
		Description: in.Description,
		OwnerID:     in.OwnerID,
	})
}

func (r *KbRepository) UpdateKB(ctx context.Context, in domain.UpdateKnowledgeBaseInput) error {
	return r.dao.UpdateKB(ctx, dao.KnowledgeBase{
		ID:          in.ID,
		Name:        in.Name,
		Description: in.Description,
	})
}

func (r *KbRepository) DeleteKB(ctx context.Context, id int64) error {
	return r.dao.DeleteKB(ctx, id)
}

func (r *KbRepository) KBNameExists(ctx context.Context, name string) (bool, error) {
	_, err := r.dao.FindKBByName(ctx, name)
	if err != nil {
		return false, nil
	}
	return true, nil
}

func toDomainKB(kb dao.KnowledgeBase) domain.KnowledgeBase {
	return domain.KnowledgeBase{
		ID:          kb.ID,
		Name:        kb.Name,
		Description: kb.Description,
		OwnerID:     kb.OwnerID,
		CreatedAt:   kb.CreatedAt,
		UpdatedAt:   kb.UpdatedAt,
	}
}
