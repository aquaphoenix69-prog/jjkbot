import { generateDigiResponse } from '@/lib/digiPersona';

export async function POST(request) {
  const { message } = await request.json();

  await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 1200));

  const { text, gif } = generateDigiResponse(message);

  return Response.json({ response: text, gif });
}
