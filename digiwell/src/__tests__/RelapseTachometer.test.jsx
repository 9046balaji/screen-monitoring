import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import RelapseTachometer from '../components/charts/RelapseTachometer';

describe('RelapseTachometer Component', () => {
  it('renders low risk correctly', () => {
    render(<RelapseTachometer risk={0.1} topFeatures={[]} onStartFocus={vi.fn()} />);
    expect(screen.getByText('10%')).toBeDefined();
    expect(screen.getByText('Low Risk')).toBeDefined();
    expect(screen.queryByText('Start Focus Mode Now')).toBeNull();
  });

  it('renders critical risk correctly and shows CTA', () => {
    const onStartMock = vi.fn();
    render(<RelapseTachometer risk={0.85} topFeatures={['Late night', 'Bad Mood']} onStartFocus={onStartMock} />);
    
    expect(screen.getByText('85%')).toBeDefined();
    expect(screen.getByText('Critical Risk')).toBeDefined();
    expect(screen.getByText(/Late night, Bad Mood/)).toBeDefined();
    
    const btn = screen.getByText('Start Focus Mode Now');
    expect(btn).toBeDefined();
    fireEvent.click(btn);
    expect(onStartMock).toHaveBeenCalled();
  });
});
