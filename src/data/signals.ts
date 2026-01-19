// 시그널 관련 유틸리티 함수
// 실제 시그널 데이터는 Supabase API에서 가져옵니다.

import { Signal, SignalCategory, SignalStatus, SignalImpact, Evidence } from "@/types/signal";

// 은행 거래 타입 (타입 정의만 유지)
export type BankTransactionType = "loan" | "deposit" | "fx" | "pension" | "payroll" | "card";

// 상대 시간 표시
export const formatRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 60) return `${diffMins}분 전`;
  if (diffHours < 24) return `${diffHours}시간 전`;
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;
  return date.toLocaleDateString('ko-KR');
};

// 날짜 포맷팅
export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};

// 은행 거래 타입 레이블
export const getBankTransactionTypeLabel = (type: BankTransactionType): string => {
  const labels: Record<BankTransactionType, string> = {
    loan: "여신",
    deposit: "수신",
    fx: "외환",
    pension: "퇴직연금",
    payroll: "급여",
    card: "카드",
  };
  return labels[type];
};
