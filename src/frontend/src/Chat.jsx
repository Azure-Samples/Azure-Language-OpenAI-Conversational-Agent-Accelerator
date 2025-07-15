// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.
import { useState, useEffect, useRef } from 'react';
import Markdown from 'react-markdown'

const Chat = () => {
    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const messageEndRef = useRef(null);
    const welcomeMessage = 'Ask a question...';

    const scrollToBottom = () => {
        messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const createSystemInput = (userMessageContent) => {
        console.log(messages);

        const lastTwoMessages = messages.slice(-2);

        // Check if either message includes "please provide more information"
        const containsFollowUpRequest = lastTwoMessages.some(msg =>
            msg.content.toLowerCase().includes("please provide more information")
        );

        const historyString = containsFollowUpRequest
            ? lastTwoMessages.map(msg => `${msg.role.toLowerCase()}: ${msg.content}`).join(", ")
            : "empty";

        const formattedString = `current_question: ${userMessageContent}, history: ${historyString}`;

        return {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                message: formattedString,
            })
        }
    };

    const parseSystemResponse = (systemResponse) => {
        const messages = systemResponse["messages"]
        return messages
    }

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
            const systemMessages = parseSystemResponse(systemResponse);
            console.log(systemMessages)

            return systemMessages;
        } catch (error) {
            console.error("Error while processing chat: ", error)
        }
    };

    const handleSendMessage = async (userMessageContent) => {
        setMessages((prevMessages) => [
            ...prevMessages, { role: "User", content: userMessageContent }
        ]);

        setIsTyping(true);
        const systemMessages = await chatWithSystem(userMessageContent);
        setIsTyping(false);

        for (const msg of systemMessages) {
            setMessages((prevMessages) => [
                ...prevMessages, { role: "System", content: msg }
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
