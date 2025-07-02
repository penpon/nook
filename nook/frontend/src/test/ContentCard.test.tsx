import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ContentCard } from '../components/ContentCard';
import type { ContentItem } from '../types';

/**
 * ContentCard記事番号表示テスト（TDD完了）
 * tmp-develop理想UI状態の核心機能をテスト
 * 
 * テスト対象: index prop による記事番号表示（1〜15番の記事番号）
 * 検証内容: 記事番号バッジの表示・スタイル・条件分岐
 * TDDサイクル: Red → Green → Refactor → Commit 完了
 */

// テスト用モックデータ
const mockContentItem: ContentItem = {
  title: 'テスト記事タイトル',
  content: 'テスト記事内容',
  url: 'https://example.com',
  source: 'test-service',
  isArticle: true
};

describe('ContentCard記事番号表示テスト', () => {
  describe('理想UI状態の記事番号「1」〜「15」表示', () => {
    it('indexが0の時、記事番号「1」が表示されること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={0} 
        />
      );
      
      // 記事番号「1」の表示確認
      const numberBadge = screen.getByText('1');
      expect(numberBadge).toBeInTheDocument();
    });

    it('indexが1の時、記事番号「2」が表示されること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={1} 
        />
      );
      
      // 記事番号「2」の表示確認
      const numberBadge = screen.getByText('2');
      expect(numberBadge).toBeInTheDocument();
    });

    it('indexが14の時、記事番号「15」が表示されること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={14} 
        />
      );
      
      // 記事番号「15」の表示確認
      const numberBadge = screen.getByText('15');
      expect(numberBadge).toBeInTheDocument();
    });

    it('indexがundefinedの時、記事番号が表示されないこと', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={undefined} 
        />
      );
      
      // 記事番号が存在しないことを確認
      expect(screen.queryByText('1')).not.toBeInTheDocument();
    });
  });

  describe('番号バッジのスタイル確認', () => {
    it('ライトモードで正しいクラスが適用されること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={0} 
        />
      );
      
      const numberBadge = screen.getByText('1');
      expect(numberBadge).toHaveClass('bg-blue-100', 'text-blue-800');
    });

    it('ダークモードで正しいクラスが適用されること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={true} 
          index={0} 
        />
      );
      
      const numberBadge = screen.getByText('1');
      expect(numberBadge).toHaveClass('dark:bg-blue-900', 'dark:text-blue-300');
    });
  });

  describe('理想UI状態のバッジデザイン確認', () => {
    it('番号バッジが丸みを帯びたデザインであること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={0} 
        />
      );
      
      const numberBadge = screen.getByText('1');
      expect(numberBadge).toHaveClass('rounded-full');
    });

    it('番号バッジに適切なパディングが設定されていること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={0} 
        />
      );
      
      const numberBadge = screen.getByText('1');
      expect(numberBadge).toHaveClass('px-2', 'py-1');
    });

    it('番号バッジに適切なマージンが設定されていること', () => {
      render(
        <ContentCard 
          item={mockContentItem} 
          darkMode={false} 
          index={0} 
        />
      );
      
      const numberBadge = screen.getByText('1');
      expect(numberBadge).toHaveClass('mr-3');
    });
  });
});