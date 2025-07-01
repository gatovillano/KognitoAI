import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';

interface MentionListProps {
  items: { id: string; label: string }[];
  command: (item: { id: string; label: string }) => void;
}

export const MentionList = forwardRef((props: MentionListProps, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const selectItem = (index: number) => {
    const item = props.items[index];
    if (item) {
      props.command(item);
    }
  };

  const upHandler = () => {
    setSelectedIndex((selectedIndex + props.items.length - 1) % props.items.length);
  };

  const downHandler = () => {
    setSelectedIndex((selectedIndex + 1) % props.items.length);
  };

  const enterHandler = () => {
    selectItem(selectedIndex);
  };

  useEffect(() => setSelectedIndex(0), [props.items]);

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }: { event: KeyboardEvent }) => {
      if (event.key === 'ArrowUp') {
        upHandler();
        return true;
      }
      if (event.key === 'ArrowDown') {
        downHandler();
        return true;
      }
      if (event.key === 'Enter') {
        enterHandler();
        return true;
      }
      return false;
    },
  }));

  return (
    <div className="bg-white text-black rounded-lg shadow-lg p-2">
      {props.items.length ? (
        props.items.map((item, index) => (
          <button
            className={`w-full text-left p-2 rounded-md ${index === selectedIndex ? 'bg-gray-200' : ''}`}
            key={index}
            onClick={() => selectItem(index)}
          >
            {item.label}
          </button>
        ))
      ) : (
        <div className="p-2">No results</div>
      )}
    </div>
  );
});

MentionList.displayName = 'MentionList';
