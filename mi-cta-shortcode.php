<?php
function mi_cta_shortcode($atts) {
    // Atributos por defecto
    $atts = shortcode_atts(
        array(
            'titulo1' => 'Título de la CTA 1',
            'descripcion1' => 'Breve descripción para la llamada a la acción número uno. ¡Haz clic para saber más!',
            'boton_texto1' => 'Saber Más',
            'boton_url1' => '#',

            'titulo2' => 'Título de la CTA 2',
            'descripcion2' => 'Una segunda descripción para tu llamada a la acción. ¡No te quedes sin descubrirlo!',
            'boton_texto2' => 'Ver Ofertas',
            'boton_url2' => '#',

            'titulo3' => 'Título de la CTA 3',
            'descripcion3' => 'La tercera y última descripción. ¡Aprovecha esta oportunidad única!',
            'boton_texto3' => 'Contáctanos',
            'boton_url3' => '#',
        ),
        $atts,
        'mi_cta'
    );

    ob_start();
    ?>
    <style>
        .cta-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            margin: 40px 0;
        }
        .cta-column {
            flex: 1;
            min-width: 280px;
            max-width: 350px;
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            padding: 30px;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .cta-column:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        .cta-column h3 {
            font-size: 1.8em;
            color: #333;
            margin-bottom: 15px;
            font-weight: 700;
        }
        .cta-column p {
            font-size: 1.1em;
            color: #666;
            line-height: 1.6;
            margin-bottom: 25px;
            flex-grow: 1;
        }
        .cta-button {
            display: inline-block;
            background-color: #007bff; /* Color primario */
            color: #ffffff;
            padding: 12px 25px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.05em;
            transition: background-color 0.3s ease, transform 0.3s ease;
            border: none;
            cursor: pointer;
        }
        .cta-button:hover {
            background-color: #0056b3; /* Tono más oscuro al pasar el ratón */
            transform: translateY(-2px);
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .cta-container {
                flex-direction: column;
                align-items: center;
            }
            .cta-column {
                max-width: 90%;
            }
        }
    </style>

    <div class="cta-container">
        <div class="cta-column">
            <h3><?php echo esc_html($atts['titulo1']); ?></h3>
            <p><?php echo esc_html($atts['descripcion1']); ?></p>
            <a href="<?php echo esc_url($atts['boton_url1']); ?>" class="cta-button"><?php echo esc_html($atts['boton_texto1']); ?></a>
        </div>

        <div class="cta-column">
            <h3><?php echo esc_html($atts['titulo2']); ?></h3>
            <p><?php echo esc_html($atts['descripcion2']); ?></p>
            <a href="<?php echo esc_url($atts['boton_url2']); ?>" class="cta-button"><?php echo esc_html($atts['boton_texto2']); ?></a>
        </div>

        <div class="cta-column">
            <h3><?php echo esc_html($atts['titulo3']); ?></h3>
            <p><?php echo esc_html($atts['descripcion3']); ?></p>
            <a href="<?php echo esc_url($atts['boton_url3']); ?>" class="cta-button"><?php echo esc_html($atts['boton_texto3']); ?></a>
        </div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('mi_cta', 'mi_cta_shortcode');
?>