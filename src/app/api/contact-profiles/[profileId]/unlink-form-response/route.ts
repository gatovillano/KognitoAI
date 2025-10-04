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

    // Actualizar la respuesta del formulario para desvincularla del perfil de contacto
    const result = await db.collection('form_responses').updateOne(
      { _id: new ObjectId(form_response_id), contact_profile_id: new ObjectId(profileId) },
      { $unset: { contact_profile_id: "" } } // Eliminar el campo contact_profile_id
    );

    if (result.matchedCount === 0) {
      return NextResponse.json({ message: 'Form response not found or not linked to this profile' }, { status: 404 });
    }

    return NextResponse.json({ message: 'Form response unlinked successfully' });
  } catch (error) {
    console.error('Error unlinking form response from contact profile:', error);
    return NextResponse.json({ message: 'Internal server error' }, { status: 500 });
  }
}
