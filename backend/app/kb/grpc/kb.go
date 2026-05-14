package grpc

import (
	"context"
	"io"
	"log/slog"

	"google.golang.org/protobuf/types/known/timestamppb"

	kbv1 "github.com/mymikasa/pivot/api/gen/kb/v1"
	"github.com/mymikasa/pivot/app/kb/domain"
	"github.com/mymikasa/pivot/app/kb/service"
)

type KbServer struct {
	kbv1.UnimplementedKnowledgeBaseServiceServer
	svc    service.Service
	logger *slog.Logger
}

func NewKbServer(svc service.Service, logger *slog.Logger) *KbServer {
	return &KbServer{svc: svc, logger: logger}
}

// --- KnowledgeBase CRUD ---

func (g *KbServer) CreateKnowledgeBase(ctx context.Context, req *kbv1.CreateKnowledgeBaseRequest) (*kbv1.CreateKnowledgeBaseResponse, error) {
	kb, err := g.svc.CreateKnowledgeBase(ctx, req.GetName(), req.GetDescription())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.CreateKnowledgeBaseResponse{Kb: toProtoKB(kb)}, nil
}

func (g *KbServer) ListKnowledgeBases(ctx context.Context, _ *kbv1.ListKnowledgeBasesRequest) (*kbv1.ListKnowledgeBasesResponse, error) {
	items, err := g.svc.ListKnowledgeBases(ctx)
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	pb := make([]*kbv1.KnowledgeBase, 0, len(items))
	for _, kb := range items {
		pb = append(pb, toProtoKB(kb))
	}
	return &kbv1.ListKnowledgeBasesResponse{Items: pb}, nil
}

func (g *KbServer) GetKnowledgeBase(ctx context.Context, req *kbv1.GetKnowledgeBaseRequest) (*kbv1.GetKnowledgeBaseResponse, error) {
	kb, err := g.svc.GetKnowledgeBase(ctx, req.GetId())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.GetKnowledgeBaseResponse{Kb: toProtoKB(kb)}, nil
}

func (g *KbServer) UpdateKnowledgeBase(ctx context.Context, req *kbv1.UpdateKnowledgeBaseRequest) (*kbv1.UpdateKnowledgeBaseResponse, error) {
	kb, err := g.svc.UpdateKnowledgeBase(ctx, req.GetId(), req.GetName(), req.GetDescription())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.UpdateKnowledgeBaseResponse{Kb: toProtoKB(kb)}, nil
}

func (g *KbServer) DeleteKnowledgeBase(ctx context.Context, req *kbv1.DeleteKnowledgeBaseRequest) (*kbv1.DeleteKnowledgeBaseResponse, error) {
	if err := g.svc.DeleteKnowledgeBase(ctx, req.GetId()); err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.DeleteKnowledgeBaseResponse{}, nil
}

// --- Document management ---

func (g *KbServer) UploadDocument(stream kbv1.KnowledgeBaseService_UploadDocumentServer) error {
	var kbID int64
	var filename, contentType string
	var data []byte

	for {
		req, err := stream.Recv()
		if err == io.EOF {
			break
		}
		if err != nil {
			return toGRPCError(err, g.logger)
		}
		if kbID == 0 {
			kbID = req.GetKbId()
			filename = req.GetFilename()
			contentType = req.GetContentType()
		}
		data = append(data, req.GetData()...)
	}

	doc, err := g.svc.UploadDocument(stream.Context(), kbID, filename, contentType, data)
	if err != nil {
		return toGRPCError(err, g.logger)
	}
	return stream.SendAndClose(&kbv1.UploadDocumentResponse{
		Document: toProtoDocument(doc),
	})
}

func (g *KbServer) UploadDocumentSimple(ctx context.Context, req *kbv1.UploadDocumentSimpleRequest) (*kbv1.UploadDocumentResponse, error) {
	doc, err := g.svc.UploadDocument(ctx, req.GetKbId(), req.GetFilename(), req.GetContentType(), req.GetData())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.UploadDocumentResponse{Document: toProtoDocument(doc)}, nil
}

func (g *KbServer) DownloadDocumentSimple(ctx context.Context, req *kbv1.DownloadDocumentRequest) (*kbv1.DownloadDocumentSimpleResponse, error) {
	doc, data, err := g.svc.DownloadDocument(ctx, req.GetKbId(), req.GetDocId())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.DownloadDocumentSimpleResponse{
		Filename:    doc.Filename,
		ContentType: doc.ContentType,
		Data:        data,
	}, nil
}

func (g *KbServer) ListDocuments(ctx context.Context, req *kbv1.ListDocumentsRequest) (*kbv1.ListDocumentsResponse, error) {
	items, err := g.svc.ListDocuments(ctx, req.GetKbId())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	pb := make([]*kbv1.Document, 0, len(items))
	for _, doc := range items {
		pb = append(pb, toProtoDocument(doc))
	}
	return &kbv1.ListDocumentsResponse{Items: pb}, nil
}

func (g *KbServer) DeleteDocument(ctx context.Context, req *kbv1.DeleteDocumentRequest) (*kbv1.DeleteDocumentResponse, error) {
	if err := g.svc.DeleteDocument(ctx, req.GetKbId(), req.GetDocId()); err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.DeleteDocumentResponse{}, nil
}

func (g *KbServer) DownloadDocument(req *kbv1.DownloadDocumentRequest, stream kbv1.KnowledgeBaseService_DownloadDocumentServer) error {
	doc, data, err := g.svc.DownloadDocument(stream.Context(), req.GetKbId(), req.GetDocId())
	if err != nil {
		return toGRPCError(err, g.logger)
	}
	return stream.Send(&kbv1.DownloadDocumentResponse{
		Filename:    doc.Filename,
		ContentType: doc.ContentType,
		Data:        data,
	})
}

// --- proto conversion ---

func toProtoKB(kb domain.KnowledgeBase) *kbv1.KnowledgeBase {
	return &kbv1.KnowledgeBase{
		Id:            kb.ID,
		Name:          kb.Name,
		Description:   kb.Description,
		OwnerId:       kb.OwnerID,
		DocumentCount: kb.DocumentCount,
		CreatedAt:     timestamppb.New(kb.CreatedAt),
		UpdatedAt:     timestamppb.New(kb.UpdatedAt),
	}
}

func toProtoDocument(doc domain.Document) *kbv1.Document {
	pb := &kbv1.Document{
		Id:            doc.ID,
		KbId:          doc.KBID,
		Filename:      doc.Filename,
		ContentType:   doc.ContentType,
		FileSize:      doc.FileSize,
		Status:        doc.Status,
		CreatedAt:     timestamppb.New(doc.CreatedAt),
		ParseStatus:   doc.ParseStatus,
		ParseProgress: doc.ParseProgress,
		ParseError:    doc.ParseError,
		ObjectKey:     doc.ObjectKey,
	}
	if doc.ParseTaskID != nil {
		pb.ParseTaskId = *doc.ParseTaskID
	}
	if doc.ParsedAt != nil {
		pb.ParsedAt = timestamppb.New(*doc.ParsedAt)
	}
	return pb
}

// --- Presigned URL ---

func (g *KbServer) PrepareDocumentUpload(ctx context.Context, req *kbv1.PrepareDocumentUploadRequest) (*kbv1.PrepareDocumentUploadResponse, error) {
	objectKey, uploadURL, err := g.svc.PrepareDocumentUpload(ctx, req.GetKbId(), req.GetFilename(), req.GetContentType(), req.GetFileSize())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.PrepareDocumentUploadResponse{
		ObjectKey: objectKey,
		UploadUrl: uploadURL,
	}, nil
}

func (g *KbServer) ConfirmDocumentUpload(ctx context.Context, req *kbv1.ConfirmDocumentUploadRequest) (*kbv1.ConfirmDocumentUploadResponse, error) {
	doc, err := g.svc.ConfirmDocumentUpload(ctx, req.GetKbId(), req.GetObjectKey(), req.GetFilename(), req.GetContentType(), req.GetFileSize())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.ConfirmDocumentUploadResponse{
		Document: toProtoDocument(doc),
	}, nil
}

func (g *KbServer) GetDocumentDownloadURL(ctx context.Context, req *kbv1.GetDocumentDownloadURLRequest) (*kbv1.GetDocumentDownloadURLResponse, error) {
	url, doc, err := g.svc.GetDocumentDownloadURL(ctx, req.GetKbId(), req.GetDocId())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.GetDocumentDownloadURLResponse{
		DownloadUrl: url,
		Filename:    doc.Filename,
		ContentType: doc.ContentType,
	}, nil
}

// --- Chunk & Parse ---

func (g *KbServer) ListChunks(ctx context.Context, req *kbv1.ListChunksRequest) (*kbv1.ListChunksResponse, error) {
	items, err := g.svc.ListChunks(ctx, req.GetKbId(), req.GetDocId())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	pb := make([]*kbv1.Chunk, 0, len(items))
	for _, c := range items {
		item := &kbv1.Chunk{
			Id:           c.ID,
			KbId:         c.KBID,
			DocumentId:   c.DocumentID,
			ChunkIndex:   c.ChunkIndex,
			Content:      c.Content,
			TokenCount:   c.TokenCount,
			SectionTitle: c.SectionTitle,
			SectionPath:  c.SectionPath,
			Filename:     c.Filename,
			ContentType:  c.ContentType,
			ChunkSize:    c.ChunkSize,
			ChunkOverlap: c.ChunkOverlap,
			Version:      c.Version,
		}
		if c.SourcePage != nil {
			item.SourcePage = *c.SourcePage
		}
		if c.UserID != nil {
			item.UserId = *c.UserID
		}
		if c.MilvusID != nil {
			item.MilvusId = *c.MilvusID
		}
		if !c.CreatedAt.IsZero() {
			item.CreatedAt = timestamppb.New(c.CreatedAt)
		}
		if !c.UpdatedAt.IsZero() {
			item.UpdatedAt = timestamppb.New(c.UpdatedAt)
		}
		pb = append(pb, item)
	}
	return &kbv1.ListChunksResponse{Items: pb}, nil
}

func (g *KbServer) DeleteChunk(ctx context.Context, req *kbv1.DeleteChunkRequest) (*kbv1.DeleteChunkResponse, error) {
	if err := g.svc.DeleteChunk(ctx, req.GetKbId(), req.GetDocId(), req.GetChunkIndex()); err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	return &kbv1.DeleteChunkResponse{}, nil
}

func (g *KbServer) GetParseStatus(ctx context.Context, req *kbv1.GetParseStatusRequest) (*kbv1.GetParseStatusResponse, error) {
	doc, err := g.svc.GetParseStatus(ctx, req.GetKbId(), req.GetDocId())
	if err != nil {
		return nil, toGRPCError(err, g.logger)
	}
	pb := &kbv1.GetParseStatusResponse{
		Status:   doc.ParseStatus,
		Progress: doc.ParseProgress,
		Error:    doc.ParseError,
	}
	if doc.ParsedAt != nil {
		pb.ParsedAt = timestamppb.New(*doc.ParsedAt)
	}
	return pb, nil
}
