// src/components/loaders/FancyBookLoader.tsx
import React from "react";
import "./BookLoader.css";

const BookLoader: React.FC = () => {
    return (
        <div className="flex flex-col justify-center items-center h-48">
            <div className="book-loader-wrapper">
                <div className="book-cover left"></div>

                <div className="book-pages">
                    <div className="page page1"></div>
                    <div className="page page2"></div>
                    <div className="page page3"></div>
                    <div className="page page4"></div>
                    <div className="page page5"></div>

                </div>

                <div className="book-cover right"></div>
            </div>



            <p className="mt-3 text-white italic text-sm">Consulting the archives...</p>
        </div>
    );
};

export default BookLoader;
