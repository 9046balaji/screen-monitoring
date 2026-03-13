import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import MoodJournal from '../MoodJournal';
import * as api from '../../api/digiwell';

vi.mock('../api/digiwell', () => ({
  getMoodJournals: vi.fn(() => Promise.resolve([])),
  analyzeAndSaveMoodJournal: vi.fn(),
}));

describe('MoodJournal Component', () => {
  it('renders correctly', async () => {
    render(<MoodJournal />);
    expect(screen.getByText('Mood Journal')).toBeDefined();
    await waitFor(() => {
      expect(api.getMoodJournals).toHaveBeenCalled();
    });
  });

  it('submits a journal and displays AI Insight Card', async () => {
    api.analyzeAndSaveMoodJournal.mockResolvedValueOnce({
      ai_primary_emotion: "Anxious",
      ai_distortion: ["Catastrophizing"],
      ai_reframe: "Take a breath, it's just one slip.",
      ai_microtask: { type: "breathing", duration_minutes: 1, instruction: "Breathe" }
    });

    render(<MoodJournal />);
    
    // Type into textarea
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'I feel terrible' } });

    // Submit form
    const submitButton = screen.getByText('Save & Analyze Entry');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(api.analyzeAndSaveMoodJournal).toHaveBeenCalledWith('I feel terrible', 3);
      expect(screen.getByText('AI Reflection Insight')).toBeDefined();
      expect(screen.getByText('Anxious')).toBeDefined();
      expect(screen.getByText(/Take a breath/)).toBeDefined();
    });
  });
});
