// src/components/ui/ReactionButton.tsx
import React from "react";

type Variant = "like" | "dislike";

interface ReactionButtonProps {
    variant: Variant;
    onClick?: () => void;
    disabled?: boolean;
    selected?: boolean;            // <-- NEW
    className?: string;
}

const ReactionButton: React.FC<ReactionButtonProps> = ({
    variant,
    onClick,
    disabled,
    selected = false,             // <-- NEW
    className = "",
}) => {
    const isLike = variant === "like";
    const base =
        "inline-flex items-center justify-center w-6 h-6 text-lg " +
        "opacity-80 hover:opacity-100 " +
        "transition-all duration-200 ease-out " +
        "hover:scale-110 hover:-translate-y-0.5 " +
        "hover:drop-shadow-sm " +
        "select-none";

    const selectedStyles = selected ? "opacity-100 scale-110" : "";

    return (
        <button
            type="button"
            aria-label={isLike ? "Like response" : "Dislike response"}
            onClick={onClick}
            disabled={disabled || selected}
            className={`${base} disabled:opacity-50 disabled:cursor-not-allowed ${selectedStyles} ${className}`}
            title={isLike ? "Like" : "Dislike"}
        >
            {isLike ? "👍" : "👎"}
        </button>
    );
};

export default ReactionButton;
