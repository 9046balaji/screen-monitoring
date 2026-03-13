import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CBTChat from '../components/therapy/CBTChat';
import * as api from '../api/digiwell';

vi.mock('../api/digiwell', () => ({
  startTherapySession: vi.fn(),
  respondTherapySession: vi.fn(),
}));

describe('CBTChat Component', () => {
  it('initializes and sends a message', async () => {
    api.startTherapySession.mockResolvedValueOnce({
      session_id: 'mock-session-123',
      messages: [{ role: 'assistant', content: 'Hello.' }]
    });

    api.respondTherapySession.mockResolvedValueOnce({
      messages: [
        { role: 'assistant', content: 'Hello.' },
        { role: 'user', content: 'Hi.' },
        { role: 'assistant', content: 'How are you?' }
      ],
      agent_reply: 'How are you?',
      suggested_commitment: {}
    });

    render(<CBTChat onCommitmentRecommended={vi.fn()} />);
    
    await waitFor(() => {
      expect(screen.getByText('Hello.')).toBeDefined();
    });

    const input = screen.getByPlaceholderText(/Share what's on your mind/);
    fireEvent.change(input, { target: { value: 'Hi.' } });
    
    const submitBtn = screen.getByRole('button');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.respondTherapySession).toHaveBeenCalledWith('mock-session-123', 'Hi.');
      expect(screen.getByText('How are you?')).toBeDefined();
    });
  });
});
