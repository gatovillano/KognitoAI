import { NextRequest, NextResponse } from 'next/server';
import { connectToDatabase } from '@/lib/mongodb';
import { ObjectId } from 'mongodb';

export async function POST(request: NextRequest, { params: paramsPromise }: { params: Promise<{ profileId: string }> }) {
  try {
    const params = await paramsPromise; // Esperar la resolución de la promesa de params
    const { profileId } = params; 
    const { form_response_id } = await request.json();

    if (!profileId || !form_response_id) {
      return NextResponse.json({ message: 'Missing profileId or form_response_id' }, { status: 400 });
    }

    const db = await connectToDatabase();
    const collection = db.collection('form_responses');

    // Actualizar la respuesta del formulario para vincularla al perfil de contacto
    const result = await db.collection('form_responses').updateOne(
      { _id: new ObjectId(form_response_id) },
      { $set: { contact_profile_id: new ObjectId(profileId) } }
    );

    if (result.matchedCount === 0) {
      return NextResponse.json({ message: 'Form response not found' }, { status: 404 });
    }

    return NextResponse.json({ message: 'Form response linked successfully' });
  } catch (error) {
    console.error('Error linking form response to contact profile:', error);
    return NextResponse.json({ message: 'Internal server error' }, { status: 500 });
  }
}
