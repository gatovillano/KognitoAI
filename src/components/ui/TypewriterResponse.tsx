import React, { useState, useEffect } from 'react';

interface TypewriterResponseProps {
  textToType: string;
  speed?: number; // Velocidad en milisegundos
}

const TypewriterResponse: React.FC<TypewriterResponseProps> = ({ textToType, speed = 30 }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    setDisplayedText(''); // Resetea el texto si el prop cambia
    let i = 0;
    const intervalId = setInterval(() => {
      if (i < textToType.length) {
        setDisplayedText((prevText) => prevText + textToType.charAt(i));
        i++;
      } else {
        clearInterval(intervalId);
      }
    }, speed);

    return () => {
      clearInterval(intervalId);
    };
  }, [textToType, speed]);

  return <p>{displayedText}</p>;
};

export default TypewriterResponse;
