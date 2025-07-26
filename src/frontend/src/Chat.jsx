// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
import { useState, useEffect, useRef } from 'react';
import Markdown from 'react-markdown'

const Chat = () => {
    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const [needMoreInfo, setNeedMoreInfo] = useState(false);

    const messageEndRef = useRef(null);
    const welcomeMessage = 'Ask a question...';

    const scrollToBottom = () => {
        messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const createSystemInput = (userMessageContent) => {

        const lastTwoMessages = messages.slice(-2);

        const historyMessages = needMoreInfo ? lastTwoMessages : [];
        console.log(historyMessages);

        return {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                message: userMessageContent,
                history: historyMessages,
            })
        };
    };

    const parseSystemResponse = (systemResponse) => {
        return {
            messages: systemResponse["messages"] || [],
            needMoreInfo: systemResponse["need_more_info"] || false
        };
    };

    const chatWithSystem = async (userMessageContent) => {
        try {
            const response = await fetch(
                `/chat`,
                createSystemInput(userMessageContent)
            );

            if (!response.ok) {
                throw new Error("Oops! Bad chat response.");
            }

            const systemResponse = await response.json();
            const { messages, needMoreInfo } = parseSystemResponse(systemResponse);

            console.log("System messages:", messages);
            setNeedMoreInfo(needMoreInfo);

            return { messages };
        } catch (error) {
            console.error("Error while processing chat: ", error);
            return { messages: [] };
        }
    };

    const handleSendMessage = async (userMessageContent) => {
        setMessages((prevMessages) => [
            ...prevMessages, { role: "User", content: userMessageContent }
        ]);

        setIsTyping(true);
        const { messages: systemMessages } = await chatWithSystem(userMessageContent);
        setIsTyping(false);

        for (const msg of systemMessages) {
            setMessages((prevMessages) => [
                ...prevMessages, 
                { role: "System", content: msg }
            ]);
        }
    };

    return (
        <div className="chat-container">
            <div className="chat-messages">
                {messages.length == 0 && (<div className="message.content">{welcomeMessage}</div>)}
                {messages.map((message, index) => (
                    <div key={index} tabindex="0" className={message.role === 'user' ? "message.user" : "message.agent"}>
                        <div className="message">
                            <h3 className="message-header">{message.role}</h3>
                            <Markdown className="message.content">{message.content}</Markdown>
                        </div>
                    </div>
                ))}
                {isTyping && <p className="message">System is typing...</p>}
                <div ref={messageEndRef}/>
            </div>
            <form
                className="chat-input-form"
                onSubmit={(e) => {
                    e.preventDefault();
                    const input = e.target.input.value;
                    if (input.trim() != "") {
                        handleSendMessage(input);
                        e.target.reset();
                    }
                }}
                aria-label="Chat Input Form"
            >
                <input
                    className="chat-input"
                    type="text"
                    name="input"
                    placeholder="Type your message..."
                    disabled={isTyping}/>
                <button
                    className="chat-submit-button" 
                    type="submit"
                >
                    Send
                </button>
            </form>
        </div>
    );
}

export default Chat;
