/**
 * 신규 법인 KYC 분석 - 서류 업로드 페이지
 */

import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Building2,
  FileText,
  Upload,
  Check,
  X,
  Loader2,
  AlertCircle,
  ArrowLeft,
} from "lucide-react";
import { startNewKycAnalysis } from "@/lib/api";

// 서류 타입 정의
type DocumentType = 'BIZ_REG' | 'AOI' | 'SHAREHOLDERS' | 'FINANCIAL' | 'REGISTRY';

interface DocumentInfo {
  type: DocumentType;
  label: string;
  description: string;
  required: boolean;
}

const DOCUMENT_TYPES: DocumentInfo[] = [
  {
    type: 'BIZ_REG',
    label: '사업자등록증',
    description: '사업자등록번호, 상호, 대표자, 업종 정보',
    required: true,
  },
  {
    type: 'AOI',
    label: '정관',
    description: '사업목적, 자본금, 주식 정보',
    required: false,
  },
  {
    type: 'SHAREHOLDERS',
    label: '주주명부',
    description: '주주 구성, 지분율 정보',
    required: false,
  },
  {
    type: 'FINANCIAL',
    label: '재무제표',
    description: '매출, 영업이익, 부채비율 등',
    required: false,
  },
  {
    type: 'REGISTRY',
    label: '등기부등본',
    description: '법인등록번호, 설립일, 임원 정보',
    required: false,
  },
];

interface UploadedFile {
  file: File;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
}

export default function NewKycUploadPage() {
  const navigate = useNavigate();
  const [corpName, setCorpName] = useState("");
  const [memo, setMemo] = useState("");
  const [files, setFiles] = useState<Record<DocumentType, UploadedFile | null>>({
    BIZ_REG: null,
    AOI: null,
    SHAREHOLDERS: null,
    FINANCIAL: null,
    REGISTRY: null,
  });
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 파일 선택 핸들러
  const handleFileSelect = useCallback((type: DocumentType, file: File | null) => {
    if (!file) return;

    // PDF 파일 체크
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setFiles(prev => ({
        ...prev,
        [type]: { file, status: 'error', error: 'PDF 파일만 업로드 가능합니다.' }
      }));
      return;
    }

    // 10MB 제한
    if (file.size > 10 * 1024 * 1024) {
      setFiles(prev => ({
        ...prev,
        [type]: { file, status: 'error', error: '파일 크기는 10MB 이하여야 합니다.' }
      }));
      return;
    }

    setFiles(prev => ({
      ...prev,
      [type]: { file, status: 'done' }
    }));
  }, []);

  // 파일 제거 핸들러
  const handleFileRemove = useCallback((type: DocumentType) => {
    setFiles(prev => ({
      ...prev,
      [type]: null
    }));
  }, []);

  // 분석 시작
  const handleStartAnalysis = async () => {
    // 필수 서류 체크
    if (!files.BIZ_REG || files.BIZ_REG.status !== 'done') {
      setError("사업자등록증은 필수입니다.");
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      // 업로드된 파일 목록 생성
      const uploadedFiles: { type: DocumentType; file: File }[] = [];
      Object.entries(files).forEach(([type, uploadedFile]) => {
        if (uploadedFile && uploadedFile.status === 'done') {
          uploadedFiles.push({ type: type as DocumentType, file: uploadedFile.file });
        }
      });

      // API 호출
      const result = await startNewKycAnalysis({
        corpName: corpName || undefined,
        memo: memo || undefined,
        files: uploadedFiles,
      });

      // 분석 페이지로 이동
      navigate(`/new-kyc/analysis/${result.job_id}`);
    } catch (err) {
      console.error("Analysis start failed:", err);
      setError("분석 시작에 실패했습니다. 다시 시도해주세요.");
      setIsAnalyzing(false);
    }
  };

  // 업로드된 파일 수
  const uploadedCount = Object.values(files).filter(f => f?.status === 'done').length;

  return (
    <MainLayout>
      <div className="max-w-3xl mx-auto">
        {/* 뒤로가기 */}
        <Button
          variant="ghost"
          className="-ml-2 mb-4 text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/")}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          메인으로
        </Button>

        {/* 헤더 */}
        <div className="text-center mb-8 p-6 bg-gradient-to-r from-primary/5 to-primary/10 rounded-lg border border-primary/20">
          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
            <Building2 className="w-6 h-6 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">
            신규 법인 고객 KYC 분석
          </h1>
          <p className="text-muted-foreground">
            신규 법인 고객의 제출 서류를 AI가 분석하여<br />
            리스크와 기회 요인을 사전에 파악합니다.
          </p>
        </div>

        {/* 기본 정보 입력 */}
        <div className="bg-card rounded-lg border p-6 mb-6">
          <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            기본 정보 입력 (선택)
          </h2>

          <div className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">
                기업명
              </label>
              <Input
                placeholder="서류에서 자동 추출됩니다"
                value={corpName}
                onChange={(e) => setCorpName(e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm text-muted-foreground mb-1 block">
                메모
              </label>
              <Textarea
                placeholder="예: 강남지점 방문 고객, 법인계좌 개설 희망"
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                rows={2}
              />
            </div>
          </div>
        </div>

        {/* 서류 업로드 */}
        <div className="bg-card rounded-lg border p-6 mb-6">
          <h2 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
            <Upload className="w-4 h-4" />
            서류 업로드 (PDF)
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            {DOCUMENT_TYPES.map((doc) => {
              const uploadedFile = files[doc.type];
              const isDone = uploadedFile?.status === 'done';
              const hasError = uploadedFile?.status === 'error';

              return (
                <div
                  key={doc.type}
                  className={`
                    relative border-2 rounded-lg p-4 transition-all
                    ${isDone
                      ? 'border-green-500 bg-green-50 dark:bg-green-950/20'
                      : hasError
                        ? 'border-red-500 bg-red-50 dark:bg-red-950/20'
                        : 'border-dashed border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/50'
                    }
                  `}
                >
                  <input
                    type="file"
                    accept=".pdf"
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    onChange={(e) => handleFileSelect(doc.type, e.target.files?.[0] || null)}
                    disabled={isAnalyzing}
                  />

                  <div className="text-center">
                    {/* 아이콘 */}
                    <div className={`
                      w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center
                      ${isDone
                        ? 'bg-green-500 text-white'
                        : hasError
                          ? 'bg-red-500 text-white'
                          : 'bg-muted text-muted-foreground'
                      }
                    `}>
                      {isDone ? (
                        <Check className="w-5 h-5" />
                      ) : hasError ? (
                        <X className="w-5 h-5" />
                      ) : (
                        <FileText className="w-5 h-5" />
                      )}
                    </div>

                    {/* 라벨 */}
                    <div className="font-medium text-sm mb-1">
                      {doc.label}
                      {doc.required && <span className="text-red-500 ml-1">*</span>}
                    </div>

                    {/* 상태 텍스트 */}
                    {isDone ? (
                      <div className="text-xs text-green-600 dark:text-green-400 truncate">
                        {uploadedFile.file.name}
                      </div>
                    ) : hasError ? (
                      <div className="text-xs text-red-600 dark:text-red-400">
                        {uploadedFile.error}
                      </div>
                    ) : (
                      <div className="text-xs text-muted-foreground">
                        {doc.description}
                      </div>
                    )}
                  </div>

                  {/* 제거 버튼 */}
                  {isDone && !isAnalyzing && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleFileRemove(doc.type);
                      }}
                      className="absolute top-2 right-2 w-5 h-5 rounded-full bg-muted hover:bg-red-100 flex items-center justify-center transition-colors"
                    >
                      <X className="w-3 h-3 text-muted-foreground hover:text-red-600" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertCircle className="w-4 h-4" />
            <span>
              최소 사업자등록증 1개 필수, 나머지는 선택입니다.
              서류가 많을수록 분석 정확도가 높아집니다.
            </span>
          </div>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6 flex items-center gap-2 text-red-700 dark:text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* 분석 시작 버튼 */}
        <div className="bg-card rounded-lg border p-6 text-center">
          <Button
            size="lg"
            className="gap-2 px-8"
            onClick={handleStartAnalysis}
            disabled={isAnalyzing || uploadedCount === 0}
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                분석 시작 중...
              </>
            ) : (
              <>
                <Building2 className="w-4 h-4" />
                AI 분석 시작 ({uploadedCount}개 서류)
              </>
            )}
          </Button>
          <p className="text-sm text-muted-foreground mt-3">
            분석에는 약 30초~1분 정도 소요됩니다.
          </p>
        </div>
      </div>
    </MainLayout>
  );
}
