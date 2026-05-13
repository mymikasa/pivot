package grpc

import (
	"testing"
	"time"

	"github.com/mymikasa/pivot/app/kb/domain"
)

func TestToProtoDocumentIncludesParseFields(t *testing.T) {
	taskID := int64(101)
	parsedAt := time.Now()
	doc := domain.Document{
		ID:            42,
		KBID:          7,
		Filename:      "hello.txt",
		ObjectKey:     "7/hello.txt",
		ContentType:   "text/plain",
		FileSize:      11,
		Status:        "ready",
		ParseStatus:   domain.DocumentParseStatusRunning,
		ParseTaskID:   &taskID,
		ParseProgress: 65,
		ParseError:    "",
		ParsedAt:      &parsedAt,
		CreatedAt:     time.Now(),
	}

	pb := toProtoDocument(doc)

	if pb.ObjectKey != "7/hello.txt" {
		t.Fatalf("object_key = %q", pb.ObjectKey)
	}
	if pb.ParseStatus != domain.DocumentParseStatusRunning {
		t.Fatalf("parse_status = %q", pb.ParseStatus)
	}
	if pb.ParseTaskId != taskID {
		t.Fatalf("parse_task_id = %d", pb.ParseTaskId)
	}
	if pb.ParseProgress != 65 {
		t.Fatalf("parse_progress = %d", pb.ParseProgress)
	}
	if pb.ParsedAt == nil {
		t.Fatal("parsed_at is nil")
	}
}
