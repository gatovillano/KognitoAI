import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { nombre, organizacion, email, categoria, mensaje } = body;

    if (!nombre || !email || !mensaje) {
      return NextResponse.json(
        { error: "Campos requeridos faltantes (nombre, email, mensaje)." },
        { status: 400 }
      );
    }

    const recipientEmail = "contacto@kognitoai.cloud";
    const timestamp = new Date().toISOString();

    // Log de la solicitud recibida
    console.log(`[FORMULARIO DE CONTACTO] Nueva solicitud para <${recipientEmail}>`, {
      timestamp,
      nombre,
      organizacion: organizacion || "N/A",
      email,
      categoria: categoria || "beta_tester",
      mensaje
    });

    return NextResponse.json({
      success: true,
      message: `Solicitud recibida exitosamente para ${recipientEmail}`,
      timestamp
    });
  } catch (error: any) {
    console.error("Error al procesar el contacto:", error);
    return NextResponse.json(
      { error: "Error al procesar la solicitud de contacto." },
      { status: 500 }
    );
  }
}
