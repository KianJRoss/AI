# Modern AI Chat UI Patterns & Implementation Guide (2025)

**Last Updated**: 2025-11-12
**Research Focus**: Production-ready patterns for AI chat interfaces, context management, and multi-agent systems

---

## Table of Contents

1. [Modern Chat UI Patterns](#1-modern-chat-ui-patterns)
2. [Context Management & Token Efficiency](#2-context-management--token-efficiency)
3. [Sub-agent Communication Patterns](#3-sub-agent-communication-patterns)
4. [Code Examples & Implementation](#4-code-examples--implementation)

---

## 1. Modern Chat UI Patterns

### 1.1 Core Design Principles (2025)

**Minimalist & Functional**
- ChatGPT, Claude, and Gemini maintain clean, two-column layouts
- Left sidebar for conversation history and projects
- Main area for active chat
- Emphasis on consistency, accessibility, and subtle interactivity

**What Makes Them Feel Modern:**
1. **Generous spacing** - No cramped interfaces
2. **Smooth animations** - Hover effects, transitions, streaming text
3. **Clear visual hierarchy** - Distinguished user/AI messages
4. **Responsive design** - Adapts to all screen sizes
5. **Dark mode support** - System-aware theming

### 1.2 Message Bubble Design

**Industry Standards (2025):**

```css
/* Message Bubble Specifications */
.message-bubble {
  /* Dimensions */
  max-width: 65ch; /* ~600px, optimal reading width */
  min-height: 40px;

  /* Spacing */
  padding: 12px 16px; /* Internal padding */
  margin-bottom: 16px; /* Gap between messages */

  /* Visual */
  border-radius: 16px; /* Rounded corners */
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05); /* Subtle depth */
}

/* User messages (right-aligned) */
.message-user {
  background: hsl(215 80% 50%); /* Primary blue */
  color: white;
  margin-left: auto;
  border-bottom-right-radius: 4px; /* Tail effect */
}

/* AI messages (left-aligned) */
.message-assistant {
  background: hsl(0 0% 96%); /* Light gray */
  color: hsl(0 0% 10%);
  margin-right: auto;
  border-bottom-left-radius: 4px;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .message-assistant {
    background: hsl(0 0% 14%);
    color: hsl(0 0% 90%);
  }
}
```

**Key Metrics:**
- **20px top padding**, 10px sides, 15px bottom = optimal readability
- **16px spacing between bubbles** = clear conversation flow
- **72% increase in engagement** with well-designed bubbles (industry research)
- **200% more time spent** when messages include visual elements

### 1.3 Streaming Message Display

**The "Typewriter Effect" Pattern:**

```typescript
// React hook for streaming text display
function useStreamingText(fullText: string, speed: number = 20) {
  const [displayText, setDisplayText] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setIsComplete(false);
    let i = 0;

    const intervalId = setInterval(() => {
      setDisplayText(fullText.slice(0, i));
      i++;

      if (i > fullText.length) {
        clearInterval(intervalId);
        setIsComplete(true);
      }
    }, speed);

    return () => clearInterval(intervalId);
  }, [fullText, speed]);

  return { displayText, isComplete };
}

// Usage
function StreamingMessage({ content }: { content: string }) {
  const { displayText, isComplete } = useStreamingText(content);

  return (
    <div className="message-assistant">
      {displayText}
      {!isComplete && <Cursor />}
    </div>
  );
}

// Animated cursor component
function Cursor() {
  return (
    <svg viewBox="8 4 8 16" className="inline-block w-[1ch] animate-pulse">
      <rect x="10" y="6" width="4" height="12" fill="currentColor" />
    </svg>
  );
}
```

**Advanced: Smooth Buffered Streaming**

```typescript
// Decouples network speed from display speed
function useSmoothStreaming(chunks: string[], typewriterSpeed: number = 5) {
  const [stream, setStream] = useState('');
  const streamIndexRef = useRef(0);
  const lastTimeRef = useRef(0);
  const animationRef = useRef<number>();

  useEffect(() => {
    const fullText = chunks.join('');

    const animate = (time: number) => {
      // Only advance if enough time has passed
      if (time - lastTimeRef.current > typewriterSpeed) {
        streamIndexRef.current++;
        setStream(fullText.slice(0, streamIndexRef.current));
        lastTimeRef.current = time;
      }

      // Continue until all text is displayed
      if (streamIndexRef.current < fullText.length) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [chunks, typewriterSpeed]);

  return stream;
}
```

**Best Practices:**
- **5ms per character** = 200 chars/sec (optimal readability)
- **20ms per character** = 50 chars/sec (slower, more dramatic)
- Use `requestAnimationFrame` for 60fps smoothness
- Buffer network chunks separately from display animation
- Allow users to skip animation (click to complete)

### 1.4 Markdown & Code Rendering

**Production Pattern: React Markdown with Streaming Support**

```typescript
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

// Handle incomplete markdown during streaming
function parseIncompleteMarkdown(text: string): string {
  if (!text) return text;
  let result = text;

  // Auto-close bold formatting
  const boldPairs = (result.match(/\*\*/g) || []).length;
  if (boldPairs % 2 === 1) result += '**';

  // Auto-close italic formatting
  const italicPairs = (result.match(/__/g) || []).length;
  if (italicPairs % 2 === 1) result += '__';

  // Auto-close inline code (but not code blocks)
  const codeBlockPairs = (result.match(/```/g) || []).length;
  const insideCodeBlock = codeBlockPairs % 2 === 1;

  if (!insideCodeBlock) {
    let singleBackticks = 0;
    for (let i = 0; i < result.length; i++) {
      if (result[i] === '`' && result.substring(i, i + 3) !== '```') {
        singleBackticks++;
      }
    }
    if (singleBackticks % 2 === 1) result += '`';
  }

  // Remove unterminated links
  const linkPattern = /(!?\[)([^\]]*?)$/;
  const linkMatch = result.match(linkPattern);
  if (linkMatch) {
    const startIndex = result.lastIndexOf(linkMatch[1]);
    result = result.substring(0, startIndex);
  }

  return result;
}

// Main response component
export function Response({ children, streaming = false }) {
  const content = streaming ? parseIncompleteMarkdown(children) : children;

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : 'text';

          if (!inline) {
            return (
              <CodeBlock
                code={String(children).replace(/\n$/, '')}
                language={language}
              />
            );
          }

          return (
            <code
              className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm"
              {...props}
            >
              {children}
            </code>
          );
        },
        // Custom rendering for other elements...
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

### 1.5 Code Block Component

```typescript
// Dual-theme code block with copy functionality
export function CodeBlock({ code, language, showLineNumbers = false }) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-4 rounded-md border overflow-hidden">
      {/* Light theme */}
      <SyntaxHighlighter
        className="dark:hidden"
        language={language}
        style={oneLight}
        showLineNumbers={showLineNumbers}
      >
        {code}
      </SyntaxHighlighter>

      {/* Dark theme */}
      <SyntaxHighlighter
        className="hidden dark:block"
        language={language}
        style={oneDark}
        showLineNumbers={showLineNumbers}
      >
        {code}
      </SyntaxHighlighter>

      {/* Copy button */}
      <button
        onClick={copyToClipboard}
        className="absolute top-2 right-2 p-2 rounded bg-background/80 hover:bg-background"
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </button>
    </div>
  );
}
```

**Styling Specifications:**
- **Font**: Monospace, 14px (0.875rem)
- **Padding**: 16px (1rem) internal
- **Line height**: 1.5
- **Border radius**: 8px (rounded-md)
- **Copy button**: Absolute positioned top-right with backdrop blur
- **Theme switching**: CSS-based (no JS flicker)

### 1.6 Table & Math Rendering

```typescript
// Table component with overflow handling
components: {
  table({ children }) {
    return (
      <div className="my-4 overflow-x-auto">
        <table className="w-full border-collapse border">
          {children}
        </table>
      </div>
    );
  },

  // Math rendering (via KaTeX)
  // Just include rehype-katex and remark-math plugins
  // Inline: $E = mc^2$
  // Block: $$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$$
}
```

### 1.7 Tool/Function Calling Visualization

**Pattern from AgentBoard:**

```typescript
// Log and display tool calls
interface ToolCall {
  name: string;
  arguments: Record<string, any>;
  result?: any;
  timestamp: number;
  duration?: number;
}

function ToolCallDisplay({ call }: { call: ToolCall }) {
  return (
    <div className="my-2 rounded-lg border border-blue-200 bg-blue-50 p-3">
      <div className="flex items-center gap-2 mb-2">
        <ToolIcon className="text-blue-600" />
        <span className="font-medium text-blue-900">{call.name}</span>
        {call.duration && (
          <span className="text-xs text-blue-600">
            {call.duration}ms
          </span>
        )}
      </div>

      <details className="text-sm">
        <summary className="cursor-pointer text-blue-700">
          View details
        </summary>
        <div className="mt-2 space-y-2">
          <div>
            <div className="font-medium text-gray-700">Arguments:</div>
            <pre className="mt-1 rounded bg-white p-2 text-xs overflow-x-auto">
              {JSON.stringify(call.arguments, null, 2)}
            </pre>
          </div>

          {call.result && (
            <div>
              <div className="font-medium text-gray-700">Result:</div>
              <pre className="mt-1 rounded bg-white p-2 text-xs overflow-x-auto">
                {JSON.stringify(call.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
```

**Visual Hierarchy for Multi-Stage Workflows:**

```typescript
// Agent loop stages: OBSERVE → PLAN → ACT → REFLECT
function AgentWorkflowVisualization({ stages }: { stages: Stage[] }) {
  return (
    <div className="my-4 space-y-2">
      {stages.map((stage, idx) => (
        <div key={idx} className="flex items-start gap-3">
          <div className="flex flex-col items-center">
            <div className={`
              w-8 h-8 rounded-full flex items-center justify-center
              ${stage.status === 'complete' ? 'bg-green-100 text-green-700' : ''}
              ${stage.status === 'active' ? 'bg-blue-100 text-blue-700 animate-pulse' : ''}
              ${stage.status === 'pending' ? 'bg-gray-100 text-gray-400' : ''}
            `}>
              {idx + 1}
            </div>
            {idx < stages.length - 1 && (
              <div className="w-0.5 h-8 bg-gray-200 my-1" />
            )}
          </div>

          <div className="flex-1">
            <div className="font-medium">{stage.name}</div>
            <div className="text-sm text-gray-600">{stage.description}</div>
            {stage.duration && (
              <div className="text-xs text-gray-500 mt-1">
                {stage.duration}ms
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

### 1.8 Long Conversation Handling

**Strategies Used by Production Systems:**

1. **Virtual Scrolling** - Only render visible messages
2. **Message Grouping** - Collapse consecutive messages from same sender
3. **Lazy Loading** - Load older messages on scroll
4. **Search & Jump** - Quick navigation to specific messages
5. **Session Management** - Archive old conversations

```typescript
// Virtual scrolling for long conversations
import { useVirtualizer } from '@tanstack/react-virtual';

function ConversationView({ messages }: { messages: Message[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100, // Estimate message height
    overscan: 5, // Render 5 extra items above/below viewport
  });

  return (
    <div ref={parentRef} className="h-full overflow-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            <MessageBubble message={messages[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 1.9 Design Tokens (Tailwind/shadcn Pattern)

```css
/* CSS Variables for theming */
@layer base {
  :root {
    /* Colors */
    --background: 0 0% 100%;
    --foreground: 0 0% 10%;
    --muted: 0 0% 96%;
    --muted-foreground: 0 0% 45%;
    --primary: 215 80% 50%;
    --primary-foreground: 0 0% 100%;
    --border: 0 0% 90%;

    /* Spacing */
    --spacing-xs: 0.25rem;  /* 4px */
    --spacing-sm: 0.5rem;   /* 8px */
    --spacing-md: 1rem;     /* 16px */
    --spacing-lg: 1.5rem;   /* 24px */
    --spacing-xl: 2rem;     /* 32px */

    /* Border radius */
    --radius-sm: 0.25rem;   /* 4px */
    --radius-md: 0.5rem;    /* 8px */
    --radius-lg: 1rem;      /* 16px */

    /* Typography */
    --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --font-mono: "SF Mono", Monaco, "Cascadia Code", monospace;
    --text-xs: 0.75rem;     /* 12px */
    --text-sm: 0.875rem;    /* 14px */
    --text-base: 1rem;      /* 16px */
    --text-lg: 1.125rem;    /* 18px */
  }

  .dark {
    --background: 0 0% 10%;
    --foreground: 0 0% 90%;
    --muted: 0 0% 14%;
    --muted-foreground: 0 0% 60%;
    --border: 0 0% 20%;
  }
}
```

---

## 2. Context Management & Token Efficiency

### 2.1 The Context Window Problem (2025)

**Current Landscape:**
- **GPT-4o**: 128,000 tokens (200K for reasoning models)
- **Claude Sonnet 4**: 1,000,000 tokens (expanded from 200K)
- **Gemini Flash 2.0**: 1,000,000 tokens
- **Future (Q4 2025)**: 100M token models planned

**Cost Reality:**
- Input tokens: $0.25 - $15 per million
- Output tokens: $1.25 - $75 per million
- **Projected market**: $2.6B for context optimization tools by 2026

**The Fundamental Issue:**
> "Models do not use their context uniformly; instead, their performance grows increasingly unreliable as input length grows." - Chroma Research on Context Rot (Hong et al., 2025)

### 2.2 Core Context Engineering Principle

**Anthropic's Definition:**
> Context engineering is "curating and maintaining the optimal set of tokens during LLM inference" - treating it as the natural evolution beyond prompt engineering.

**Key Philosophy:**
Treat context as a **scarce, high-value resource** with the same rigor as managing CPU time or memory.

### 2.3 Context Compaction Strategies

#### Pattern 1: Sequence-Based Compaction (10x Extension)

```typescript
interface CompactionConfig {
  maxTokens: number;           // 2000 - size of each summary
  tokenThreshold: number;      // 80000 - trigger compaction
  retentionWindow: number;     // 6 - keep last N messages verbatim
  model: string;               // Fast model for summarization
}

// Identify compactable sequences
type MessageSequence = [
  AssistantMessage,  // Initial response
  ToolCall[],        // Function calls
  ToolResult[],      // Function results
  AssistantMessage   // Final response
];

async function compactContext(
  messages: Message[],
  config: CompactionConfig
): Promise<Message[]> {
  // 1. Estimate tokens (logarithmic sampling for speed)
  const totalTokens = estimateTokens(messages);

  if (totalTokens < config.tokenThreshold) {
    return messages; // No compaction needed
  }

  // 2. Identify compactable sequences (preserve user messages)
  const sequences = identifySequences(messages);

  // 3. Keep recent messages intact
  const recentMessages = messages.slice(-config.retentionWindow);
  const oldMessages = messages.slice(0, -config.retentionWindow);

  // 4. Compact old sequences
  const summaries: Message[] = [];

  for (const seq of sequences) {
    const summary = await summarizeSequence(seq, {
      preserveCodeBlocks: seq.hasCode && seq.codeLength < 50,
      preserveErrorMessages: true,
      preserveFilePaths: true,
      trackDecisions: true,
      trackUnresolvedIssues: true,
    });

    // 5. Entropy check (prevent over-compression)
    const entropy = calculateEntropy(summary);
    if (entropy < MINIMUM_INFORMATION_DENSITY) {
      // Keep original if summary loses too much info
      summaries.push(...seq.messages);
    } else {
      summaries.push({
        role: 'user',
        content: `[SUMMARY]\n${summary}`,
      });
    }
  }

  return [...summaries, ...recentMessages];
}

// Specialized summarization prompt
const COMPACTION_PROMPT = `
Summarize this conversation sequence, preserving:
1. Primary objectives and success criteria
2. File changes with exact paths and line numbers
3. Action logs of important operations
4. Technical relationships between components
5. Unresolved bugs or issues

Output format:
OBJECTIVES: [list]
CHANGES: [file paths and modifications]
ACTIONS: [chronological log]
ISSUES: [unresolved items]
CONTEXT: [key technical details]
`;
```

**Key Technique: Pattern-Based Detection**
- Preserves semantic units (assistant → tools → result → response)
- Unlike time-based or token-based chunking, maintains conversational flow
- **Achieves 90% reduction** on older exchanges

#### Pattern 2: Hierarchical Summarization

```typescript
interface MemoryTier {
  tier: 'short' | 'medium' | 'long';
  tokenBudget: number;
  strategy: 'verbatim' | 'compressed' | 'extracted';
}

const MEMORY_HIERARCHY: MemoryTier[] = [
  { tier: 'short', tokenBudget: 8000, strategy: 'verbatim' },    // Last 10-15 messages
  { tier: 'medium', tokenBudget: 4000, strategy: 'compressed' }, // Summaries
  { tier: 'long', tokenBudget: 1000, strategy: 'extracted' },    // Key facts only
];

class HierarchicalMemory {
  private shortTerm: Message[] = [];
  private mediumTerm: Summary[] = [];
  private longTerm: Fact[] = [];

  async addMessage(message: Message) {
    this.shortTerm.push(message);

    // Check if short-term is full
    if (this.getTokenCount(this.shortTerm) > MEMORY_HIERARCHY[0].tokenBudget) {
      await this.promote();
    }
  }

  private async promote() {
    // Move oldest short-term messages to medium-term (compressed)
    const toCompress = this.shortTerm.slice(0, 5);
    const summary = await this.compress(toCompress);
    this.mediumTerm.push(summary);
    this.shortTerm = this.shortTerm.slice(5);

    // Check if medium-term is full
    if (this.getTokenCount(this.mediumTerm) > MEMORY_HIERARCHY[1].tokenBudget) {
      // Extract key facts to long-term
      const toExtract = this.mediumTerm.slice(0, 2);
      const facts = await this.extractFacts(toExtract);
      this.longTerm.push(...facts);
      this.mediumTerm = this.mediumTerm.slice(2);
    }
  }

  getContext(): Message[] {
    // Reconstruct context from all tiers
    return [
      ...this.longTermToMessages(),
      ...this.mediumTermToMessages(),
      ...this.shortTerm,
    ];
  }
}
```

**Benefits:**
- Recent context stays detailed (high fidelity)
- Older context progressively compresses
- Ancient context becomes searchable facts
- Predictable token usage

#### Pattern 3: Sliding Window with Summarization

```typescript
class SlidingWindowMemory {
  private readonly WINDOW_SIZE = 20; // Number of messages
  private readonly SUMMARY_POSITION = 5; // Where to inject summary

  private messages: Message[] = [];
  private historySummary: string = '';

  async addMessage(message: Message) {
    this.messages.push(message);

    if (this.messages.length > this.WINDOW_SIZE) {
      // Summarize messages that will slide out
      const toSummarize = this.messages.slice(0, 10);
      const newSummary = await this.summarize(toSummarize);

      // Merge with existing summary
      this.historySummary = await this.mergeSummaries(
        this.historySummary,
        newSummary
      );

      // Keep only recent messages
      this.messages = this.messages.slice(10);
    }
  }

  getContext(): Message[] {
    if (!this.historySummary) {
      return this.messages;
    }

    // Inject summary at strategic position
    return [
      ...this.messages.slice(0, this.SUMMARY_POSITION),
      {
        role: 'system',
        content: `Previous conversation summary:\n${this.historySummary}`
      },
      ...this.messages.slice(this.SUMMARY_POSITION),
    ];
  }
}
```

### 2.4 Importance-Based Prioritization

```typescript
// Semantic similarity scoring for message relevance
interface MessageScore {
  message: Message;
  relevanceScore: number;
  importanceScore: number;
  recencyScore: number;
  finalScore: number;
}

class ImportanceScorer {
  private embedding: EmbeddingModel;

  async scoreMessage(
    message: Message,
    currentQuery: string,
    conversationContext: Message[]
  ): Promise<number> {
    // 1. Semantic relevance to current query
    const relevance = await this.semanticSimilarity(
      message.content,
      currentQuery
    );

    // 2. Intrinsic importance (has decisions, errors, etc.)
    const importance = this.calculateImportance(message);

    // 3. Recency (exponential decay)
    const recency = this.calculateRecency(message);

    // 4. Combined score
    return (
      relevance * 0.5 +      // 50% weight on relevance
      importance * 0.3 +     // 30% weight on importance
      recency * 0.2          // 20% weight on recency
    );
  }

  private calculateImportance(message: Message): number {
    let score = 0;

    // High importance indicators
    if (message.content.match(/error|exception|failed/i)) score += 0.3;
    if (message.content.match(/decision|chose|selected/i)) score += 0.2;
    if (message.toolCalls?.length > 0) score += 0.15;
    if (message.content.length > 500) score += 0.1; // Detailed responses
    if (message.content.match(/```/)) score += 0.1; // Contains code

    // Low importance indicators
    if (message.content.match(/^(ok|yes|no|thanks)$/i)) score -= 0.2;

    return Math.max(0, Math.min(1, score));
  }

  private calculateRecency(message: Message): number {
    const age = Date.now() - message.timestamp;
    const hoursPassed = age / (1000 * 60 * 60);
    // Exponential decay: 50% importance after 24 hours
    return Math.exp(-hoursPassed / 24);
  }

  private async semanticSimilarity(text1: string, text2: string): Promise<number> {
    const embedding1 = await this.embedding.embed(text1);
    const embedding2 = await this.embedding.embed(text2);
    return cosineSimilarity(embedding1, embedding2);
  }
}

// Usage: Select top K most relevant messages
async function selectRelevantContext(
  allMessages: Message[],
  query: string,
  tokenBudget: number
): Promise<Message[]> {
  const scorer = new ImportanceScorer();

  // Score all messages
  const scored = await Promise.all(
    allMessages.map(async (msg) => ({
      message: msg,
      score: await scorer.scoreMessage(msg, query, allMessages),
    }))
  );

  // Sort by score
  scored.sort((a, b) => b.score - a.score);

  // Fill budget with highest-scoring messages
  const selected: Message[] = [];
  let tokensUsed = 0;

  for (const { message } of scored) {
    const tokens = estimateTokens(message);
    if (tokensUsed + tokens > tokenBudget) break;

    selected.push(message);
    tokensUsed += tokens;
  }

  // Return in chronological order
  return selected.sort((a, b) => a.timestamp - b.timestamp);
}
```

### 2.5 External Memory with RAG

```typescript
// Store conversation externally, retrieve dynamically
class ExternalMemory {
  private vectorDB: VectorDatabase;
  private keyValueStore: KeyValueStore;

  async store(message: Message) {
    // 1. Store full message in key-value store
    await this.keyValueStore.set(message.id, message);

    // 2. Store embedding in vector database
    const embedding = await this.embed(message.content);
    await this.vectorDB.insert({
      id: message.id,
      vector: embedding,
      metadata: {
        role: message.role,
        timestamp: message.timestamp,
        hasToolCalls: message.toolCalls?.length > 0,
      },
    });
  }

  async retrieve(
    query: string,
    k: number = 5,
    filters?: Record<string, any>
  ): Promise<Message[]> {
    // 1. Find similar messages via vector search
    const queryEmbedding = await this.embed(query);
    const results = await this.vectorDB.search(queryEmbedding, k, filters);

    // 2. Fetch full messages
    const messages = await Promise.all(
      results.map(r => this.keyValueStore.get(r.id))
    );

    return messages;
  }
}

// Usage in conversation flow
class RAGConversation {
  private memory: ExternalMemory;
  private activeContext: Message[] = [];

  async sendMessage(userMessage: string) {
    // 1. Retrieve relevant history
    const relevantHistory = await this.memory.retrieve(userMessage, 10);

    // 2. Combine with active context
    const fullContext = [
      ...relevantHistory,
      ...this.activeContext.slice(-5), // Last 5 messages
      { role: 'user', content: userMessage },
    ];

    // 3. Generate response
    const response = await this.llm.complete(fullContext);

    // 4. Store both in external memory
    await this.memory.store({ role: 'user', content: userMessage });
    await this.memory.store({ role: 'assistant', content: response });

    // 5. Update active context
    this.activeContext.push(
      { role: 'user', content: userMessage },
      { role: 'assistant', content: response }
    );

    return response;
  }
}
```

**Benefits:**
- Scales to arbitrarily long conversations
- Only loads relevant context per query
- Dramatically reduces token usage
- Enables conversation search

### 2.6 Tool Result Compaction

```typescript
// Compact vs Summarize distinction
interface CompactionStrategy {
  // Compaction: Reversible (keep reference to full data)
  compact(toolResult: ToolResult): CompactedResult;

  // Summarization: Irreversible (lossy compression)
  summarize(toolResult: ToolResult): string;
}

class FileSystemToolCompaction implements CompactionStrategy {
  compact(result: ToolResult): CompactedResult {
    // Strip bulky reconstructible data, keep pointers
    return {
      type: 'file_operation',
      operation: result.operation,
      files: result.files.map(f => ({
        path: f.path,
        size: f.size,
        // Remove content, keep reference
        contentHash: hash(f.content),
      })),
      // Reference to full data
      fullDataPath: this.store(result),
    };
  }

  summarize(result: ToolResult): string {
    // Human-readable summary (lossy)
    return `Modified ${result.files.length} files: ${
      result.files.map(f => f.path).join(', ')
    }`;
  }

  async expand(compact: CompactedResult): Promise<ToolResult> {
    // Recover full data from reference
    return await this.load(compact.fullDataPath);
  }
}

// Usage pattern
class ContextManager {
  async addToolResult(result: ToolResult) {
    // Always compact first (reversible)
    const compacted = this.compaction.compact(result);
    this.context.push(compacted);

    // Summarize later if needed (irreversible)
    if (this.approachingTokenLimit()) {
      const summary = this.compaction.summarize(result);
      this.context.push({ role: 'system', content: summary });
    }
  }
}
```

**Key Principle from Anthropic:**
> "Always compact first, summarize later. Carefully track thresholds for when to trigger each."

### 2.7 Production Best Practices

**1. Multi-Mode Compaction**
```typescript
enum TaskType {
  DEBUGGING = 'debugging',
  FEATURE = 'feature',
  CODE_REVIEW = 'review',
}

function getCompactionStrategy(taskType: TaskType): CompactionStrategy {
  switch (taskType) {
    case TaskType.DEBUGGING:
      return {
        preserveStackTraces: true,
        preserveErrorMessages: true,
        compressSuccessfulOps: true,
      };
    case TaskType.FEATURE:
      return {
        preserveDecisions: true,
        preserveFileChanges: true,
        compressToolResults: true,
      };
    case TaskType.CODE_REVIEW:
      return {
        preserveComments: true,
        preserveCodeSnippets: true,
        compressApprovals: true,
      };
  }
}
```

**2. Context Budget Allocation**
```typescript
const CONTEXT_BUDGET: Record<string, number> = {
  systemPrompt: 500,        // Instructions
  recentMessages: 4000,     // Last 10-15 exchanges
  relevantHistory: 2000,    // Summarized/retrieved
  toolDefinitions: 1000,    // Function schemas
  activeFiles: 2500,        // Currently edited files
  buffer: 1000,             // Safety margin
};

function allocateContext(totalBudget: number = 12000) {
  const allocated = Object.values(CONTEXT_BUDGET).reduce((a, b) => a + b, 0);
  if (allocated > totalBudget) {
    throw new Error(`Budget exceeded: ${allocated} > ${totalBudget}`);
  }
  return CONTEXT_BUDGET;
}
```

**3. Quality Monitoring**
```typescript
class ContextQualityMonitor {
  async measureCompactionQuality(
    original: Message[],
    compacted: Message[]
  ): Promise<QualityMetrics> {
    return {
      compressionRatio: this.getTokenCount(compacted) / this.getTokenCount(original),
      informationRetention: await this.measureRetention(original, compacted),
      semanticSimilarity: await this.measureSimilarity(original, compacted),
      taskPerformance: await this.measureTaskSuccess(compacted),
    };
  }

  private async measureRetention(
    original: Message[],
    compacted: Message[]
  ): Promise<number> {
    // Ask LLM to answer questions about both versions
    const questions = this.generateQuestions(original);
    const originalAnswers = await this.answerQuestions(questions, original);
    const compactedAnswers = await this.answerQuestions(questions, compacted);

    // Compare accuracy
    return this.compareAnswers(originalAnswers, compactedAnswers);
  }
}
```

---

## 3. Sub-agent Communication Patterns

### 3.1 Agent Orchestration Overview (2025)

**Five Core Patterns (Microsoft/OpenAI):**

1. **Sequential**: Linear pipeline (A → B → C)
2. **Concurrent**: Parallel independent analysis
3. **Group Chat**: Collaborative debate with manager
4. **Handoff**: Dynamic routing based on expertise
5. **Magentic**: Manager-led dynamic task planning

### 3.2 Pattern 1: Sequential Orchestration

**Use Case**: Multistage processes with clear linear dependencies

```typescript
interface Agent {
  name: string;
  instructions: string;
  tools: Function[];
  model: string;
}

class SequentialOrchestrator {
  async execute(agents: Agent[], initialInput: any) {
    let currentContext = initialInput;
    const results = [];

    for (const agent of agents) {
      console.log(`Executing: ${agent.name}`);

      const result = await this.runAgent(agent, currentContext);
      results.push(result);

      // Output becomes next agent's input
      currentContext = result;
    }

    return results;
  }

  private async runAgent(agent: Agent, context: any) {
    const messages = [
      { role: 'system', content: agent.instructions },
      { role: 'user', content: JSON.stringify(context) },
    ];

    const response = await llm.complete({
      model: agent.model,
      messages,
      tools: agent.tools,
    });

    return response;
  }
}

// Example: Contract generation pipeline
const contractPipeline = [
  {
    name: 'Template Selector',
    instructions: 'Select appropriate contract template based on requirements',
    tools: [listTemplates, selectTemplate],
  },
  {
    name: 'Clause Customizer',
    instructions: 'Customize clauses based on client specifications',
    tools: [modifyClause, addClause, removeClause],
  },
  {
    name: 'Compliance Checker',
    instructions: 'Ensure contract meets regulatory requirements',
    tools: [checkCompliance, listViolations],
  },
  {
    name: 'Risk Assessor',
    instructions: 'Identify potential legal risks',
    tools: [analyzeRisk, generateReport],
  },
];

const orchestrator = new SequentialOrchestrator();
const finalContract = await orchestrator.execute(
  contractPipeline,
  { clientId: '123', type: 'NDA' }
);
```

**Context Efficiency:**
- Each agent only sees output from previous agent
- No accumulated context
- **Token usage**: O(n) where n = number of agents

### 3.3 Pattern 2: Concurrent Orchestration

**Use Case**: Multiple independent perspectives

```typescript
class ConcurrentOrchestrator {
  async execute(agents: Agent[], input: any) {
    // Run all agents in parallel
    const results = await Promise.all(
      agents.map(agent => this.runAgent(agent, input))
    );

    // Synthesize results
    return this.synthesize(results);
  }

  private async synthesize(results: any[]) {
    // Combine independent analyses
    return {
      analyses: results,
      consensus: await this.findConsensus(results),
      conflicts: await this.identifyConflicts(results),
    };
  }
}

// Example: Stock analysis from multiple angles
const stockAnalysts = [
  {
    name: 'Fundamental Analyst',
    instructions: 'Analyze financials, P/E ratio, revenue growth',
    tools: [getFinancials, calculateRatios],
  },
  {
    name: 'Technical Analyst',
    instructions: 'Analyze price patterns, volume, momentum',
    tools: [getPriceData, calculateIndicators],
  },
  {
    name: 'Sentiment Analyst',
    instructions: 'Analyze news sentiment, social media, insider trading',
    tools: [getNews, analyzeSentiment],
  },
  {
    name: 'ESG Analyst',
    instructions: 'Evaluate environmental, social, governance factors',
    tools: [getESGData, scoreESG],
  },
];

const orchestrator = new ConcurrentOrchestrator();
const analysis = await orchestrator.execute(
  stockAnalysts,
  { ticker: 'AAPL' }
);
```

**Context Efficiency:**
- Each agent only sees original input
- No cross-agent communication
- **Token usage**: O(k) where k = number of concurrent agents (efficient!)

### 3.4 Pattern 3: Handoff Orchestration

**Use Case**: Dynamic routing based on expertise discovery

**The Core Mechanism:**

```typescript
// Handoff is triggered by returning an Agent object
function transfer_to_agent(targetAgent: Agent): Agent {
  return targetAgent; // Special return type signals handoff
}

class HandoffOrchestrator {
  async execute(initialAgent: Agent, initialMessage: string) {
    let currentAgent = initialAgent;
    const conversationHistory: Message[] = [
      { role: 'user', content: initialMessage },
    ];

    while (true) {
      const result = await this.runAgent(currentAgent, conversationHistory);

      // Check if agent returned another agent (handoff signal)
      if (result.type === 'agent_handoff') {
        console.log(`Handoff: ${currentAgent.name} → ${result.nextAgent.name}`);
        currentAgent = result.nextAgent;

        // Context persists automatically (same conversation history)
        conversationHistory.push({
          role: 'assistant',
          content: result.message,
        });
        continue;
      }

      // Normal completion
      conversationHistory.push({
        role: 'assistant',
        content: result.message,
      });

      if (result.complete) break;

      // User's next message
      const userMessage = await getUserInput();
      conversationHistory.push({
        role: 'user',
        content: userMessage,
      });
    }

    return conversationHistory;
  }

  private async runAgent(agent: Agent, messages: Message[]) {
    const response = await llm.complete({
      model: agent.model,
      messages: [
        { role: 'system', content: agent.instructions },
        ...messages,
      ],
      tools: [...agent.tools, ...agent.handoffTools],
    });

    // Check if response contains handoff
    if (response.toolCalls?.some(tc => tc.name.startsWith('transfer_to_'))) {
      const handoffCall = response.toolCalls.find(tc =>
        tc.name.startsWith('transfer_to_')
      );
      const targetAgent = this.resolveAgent(handoffCall.name);

      return {
        type: 'agent_handoff',
        nextAgent: targetAgent,
        message: response.content,
      };
    }

    return {
      type: 'completion',
      message: response.content,
      complete: response.complete,
    };
  }
}

// Example: Customer support routing
const triageAgent = {
  name: 'Triage Agent',
  instructions: 'Understand customer issue and route to appropriate specialist',
  tools: [
    transfer_to_billing,
    transfer_to_technical,
    transfer_to_account_management,
  ],
};

const billingAgent = {
  name: 'Billing Agent',
  instructions: 'Handle billing inquiries, refunds, payment issues',
  tools: [
    processRefund,
    updatePaymentMethod,
    viewInvoices,
    transfer_to_triage,
  ],
};

const technicalAgent = {
  name: 'Technical Agent',
  instructions: 'Resolve technical issues with product',
  tools: [
    checkSystemStatus,
    resetPassword,
    escalateToEngineering,
    transfer_to_triage,
  ],
};
```

**Key Insight from OpenAI:**
> "The model is smart enough to know to call this function when it makes sense."

**Context Efficiency:**
- **Single message thread** across all agents
- No context reloading needed
- **Token usage**: O(m) where m = conversation length (same as single agent!)

### 3.5 Pattern 4: Magentic Orchestration

**Use Case**: Complex open-ended tasks requiring dynamic planning

```typescript
interface Task {
  id: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'blocked';
  assignedAgent?: Agent;
  dependencies: string[];
  result?: any;
}

class MagenticOrchestrator {
  private taskLedger: Task[] = [];
  private manager: Agent;
  private specialists: Agent[];

  async execute(goal: string) {
    // Manager creates initial task breakdown
    const initialPlan = await this.manager.plan(goal);
    this.taskLedger = initialPlan.tasks;

    while (this.hasIncompleteTasks()) {
      // Manager decides next action
      const decision = await this.manager.decide(this.taskLedger);

      if (decision.type === 'assign_task') {
        await this.executeTask(decision.task, decision.agent);
      } else if (decision.type === 'refine_plan') {
        this.taskLedger = await this.manager.refinePlan(this.taskLedger);
      } else if (decision.type === 'add_task') {
        this.taskLedger.push(decision.newTask);
      }

      // Update ledger with results
      this.updateLedger();
    }

    return this.synthesizeResults();
  }

  private async executeTask(task: Task, agent: Agent) {
    task.status = 'in_progress';

    const context = {
      task: task.description,
      ledger: this.taskLedger,
      previousResults: this.getRelevantResults(task),
    };

    const result = await agent.execute(context);

    task.result = result;
    task.status = 'completed';
  }

  private getRelevantResults(task: Task): any[] {
    // Only provide results from dependencies (not all tasks)
    return task.dependencies.map(depId =>
      this.taskLedger.find(t => t.id === depId)?.result
    ).filter(Boolean);
  }
}

// Example: SRE incident response
const sreManager = {
  name: 'SRE Manager',
  instructions: `
    Coordinate incident response by:
    1. Breaking down incident into diagnostic tasks
    2. Assigning tasks to specialists
    3. Refining plan based on findings
    4. Building remediation strategy
  `,
  tools: [assignTask, refinePlan, addTask, completeLedger],
};

const specialists = [
  {
    name: 'Diagnostics Agent',
    instructions: 'Analyze logs, metrics, traces to identify root cause',
    tools: [queryLogs, getMetrics, traceRequests],
  },
  {
    name: 'Infrastructure Agent',
    instructions: 'Check infrastructure health, resource usage, network',
    tools: [checkServers, checkDatabase, checkNetwork],
  },
  {
    name: 'Rollback Agent',
    instructions: 'Safely rollback deployments or configuration changes',
    tools: [rollbackDeployment, revertConfig, scaleResources],
  },
  {
    name: 'Communication Agent',
    instructions: 'Update stakeholders, create incident report',
    tools: [sendUpdate, createIncidentReport, notifyTeam],
  },
];

const orchestrator = new MagenticOrchestrator(sreManager, specialists);
await orchestrator.execute('Resolve 500 errors on checkout service');
```

**Context Efficiency:**
- Manager maintains ledger (lightweight task list)
- Specialists only see relevant task context
- **Token usage**: O(m + n*k) where m=ledger, n=tasks, k=avg context per task

### 3.6 Shared Context vs Independent Agents

```typescript
// Anti-pattern: Re-feeding all context to each agent
class NaiveOrchestrator {
  async execute(agents: Agent[], input: string) {
    const fullHistory: Message[] = [];

    for (const agent of agents) {
      // BAD: Every agent sees entire history
      const response = await agent.execute([
        ...fullHistory,  // This grows linearly!
        { role: 'user', content: input },
      ]);

      fullHistory.push(...response.messages);
    }

    // Token usage: O(n²) - quadratic growth!
  }
}

// Pattern: Minimal context handoff
class EfficientOrchestrator {
  async execute(agents: Agent[], input: string) {
    let currentSummary = input;
    const results = [];

    for (const agent of agents) {
      // GOOD: Each agent sees only summary of previous work
      const response = await agent.execute({
        role: 'user',
        content: `Previous work: ${currentSummary}\n\nYour task: ${agent.task}`,
      });

      results.push(response);

      // Compress for next agent
      currentSummary = await this.summarize(response);
      // Typically 1000-2000 tokens regardless of conversation length
    }

    // Token usage: O(n) - linear growth!
    return results;
  }
}
```

**Microsoft Guidance:**
> "If your agent can work without accumulated context and only requires a new instruction set, take that approach."

### 3.7 Agent Specialization Patterns

```typescript
// Pattern: Separation of concerns via agent specialization
interface AgentRole {
  domain: string;
  capabilities: string[];
  contextNeeds: 'full' | 'summary' | 'none';
}

const AGENT_ROLES: Record<string, AgentRole> = {
  researcher: {
    domain: 'information_gathering',
    capabilities: ['web_search', 'read_documents', 'extract_facts'],
    contextNeeds: 'none', // Can work independently
  },
  analyst: {
    domain: 'analysis',
    capabilities: ['compare', 'evaluate', 'score', 'recommend'],
    contextNeeds: 'summary', // Needs research summary
  },
  writer: {
    domain: 'content_creation',
    capabilities: ['draft', 'edit', 'format', 'cite'],
    contextNeeds: 'summary', // Needs analysis summary
  },
  reviewer: {
    domain: 'quality_assurance',
    capabilities: ['check_facts', 'check_style', 'suggest_improvements'],
    contextNeeds: 'full', // Needs original research + drafts
  },
};

class SpecializedAgent {
  constructor(
    private role: AgentRole,
    private agent: Agent
  ) {}

  async execute(context: Context): Promise<Result> {
    // Automatically filter context based on role's needs
    const relevantContext = this.filterContext(context, this.role.contextNeeds);

    return await this.agent.execute(relevantContext);
  }

  private filterContext(context: Context, needs: string): Context {
    switch (needs) {
      case 'none':
        return { instructions: context.instructions }; // Just the task
      case 'summary':
        return {
          instructions: context.instructions,
          background: context.summary, // Compressed prior work
        };
      case 'full':
        return context; // Everything
    }
  }
}
```

### 3.8 Token Efficiency Benchmarks

**LangGraph vs CrewAI vs AutoGen (Production Comparison):**

| Framework | Token Efficiency | Reason |
|-----------|-----------------|---------|
| LangGraph | **2.2x faster** | Graph-based state management passes only deltas between nodes |
| CrewAI | Baseline | Standard message accumulation |
| AutoGen | Similar to CrewAI | Full context sharing |
| LangChain | **8-9x difference** | High deliberation overhead |

**Key Insight:**
> "Framework architecture matters most for tool execution patterns and context management, not agent handoffs. Performance differences stem from tool deliberation and context synthesis, not the time spent switching between agents."

### 3.9 Production Best Practices

**1. Explicit Handoff Contracts**

```typescript
interface HandoffContract {
  from: string;
  to: string;
  payload: {
    summary: string;          // What was accomplished
    context: string;          // Relevant background
    task: string;             // What next agent should do
    constraints?: string[];   // Limitations or requirements
  };
  version: string;            // Schema version
}

function createHandoff(
  fromAgent: Agent,
  toAgent: Agent,
  data: any
): HandoffContract {
  return {
    from: fromAgent.name,
    to: toAgent.name,
    payload: {
      summary: `${fromAgent.name} completed: ${data.summary}`,
      context: data.relevantContext,
      task: toAgent.task,
    },
    version: '1.0',
  };
}
```

**2. Context Checkpointing**

```typescript
class CheckpointedOrchestrator {
  private checkpoints: Map<string, Context> = new Map();

  async executeWithCheckpoints(agents: Agent[], input: string) {
    let currentContext = input;

    for (let i = 0; i < agents.length; i++) {
      // Save checkpoint before agent execution
      this.checkpoints.set(`agent_${i}_input`, currentContext);

      try {
        const result = await agents[i].execute(currentContext);

        // Save checkpoint after agent execution
        this.checkpoints.set(`agent_${i}_output`, result);

        currentContext = result;
      } catch (error) {
        // Can recover from last checkpoint
        console.log(`Agent ${i} failed, recovering from checkpoint`);
        currentContext = this.checkpoints.get(`agent_${i-1}_output`);
        // Retry or skip
      }
    }

    return currentContext;
  }

  async recover(checkpointId: string): Promise<Context> {
    return this.checkpoints.get(checkpointId);
  }
}
```

**3. Observability**

```typescript
interface AgentMetrics {
  agentName: string;
  startTime: number;
  endTime: number;
  tokensUsed: {
    input: number;
    output: number;
  };
  toolCalls: number;
  handoffs: number;
  errors: number;
}

class ObservableOrchestrator {
  private metrics: AgentMetrics[] = [];

  async execute(agents: Agent[], input: string) {
    for (const agent of agents) {
      const startTime = Date.now();
      const startTokens = this.getTokenCount();

      const result = await agent.execute(input);

      const endTime = Date.now();
      const endTokens = this.getTokenCount();

      this.metrics.push({
        agentName: agent.name,
        startTime,
        endTime,
        tokensUsed: {
          input: result.usage.promptTokens,
          output: result.usage.completionTokens,
        },
        toolCalls: result.toolCalls?.length || 0,
        handoffs: result.handoffs || 0,
        errors: result.errors || 0,
      });
    }

    // Log metrics for analysis
    this.logMetrics();
  }

  getAggregateMetrics() {
    return {
      totalTokens: this.metrics.reduce((sum, m) =>
        sum + m.tokensUsed.input + m.tokensUsed.output, 0
      ),
      totalTime: this.metrics.reduce((sum, m) =>
        sum + (m.endTime - m.startTime), 0
      ),
      avgTokensPerAgent: this.metrics.length > 0
        ? this.metrics.reduce((sum, m) =>
            sum + m.tokensUsed.input + m.tokensUsed.output, 0
          ) / this.metrics.length
        : 0,
    };
  }
}
```

---

## 4. Code Examples & Implementation

### 4.1 Complete Chat Interface (React + TypeScript)

```typescript
// components/Chat.tsx
import { useState, useRef, useEffect } from 'react';
import { Message, StreamingMessage } from './Message';
import { InputArea } from './InputArea';

interface ChatProps {
  apiEndpoint: string;
}

export function Chat({ apiEndpoint }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  async function sendMessage(content: string) {
    // Add user message
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Start streaming
    setIsStreaming(true);
    setStreamingContent('');

    try {
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMessage],
        }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';

      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;

        const chunk = decoder.decode(value);
        accumulated += chunk;
        setStreamingContent(accumulated);
      }

      // Finalize assistant message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: accumulated,
        timestamp: Date.now(),
      }]);
      setStreamingContent('');
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <header className="p-4 border-b">
        <h1 className="text-xl font-semibold">AI Chat</h1>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, idx) => (
          <Message key={idx} message={message} />
        ))}

        {isStreaming && (
          <StreamingMessage content={streamingContent} />
        )}

        <div ref={scrollRef} />
      </div>

      {/* Input */}
      <InputArea
        onSend={sendMessage}
        disabled={isStreaming}
      />
    </div>
  );
}
```

### 4.2 Message Component with Markdown

```typescript
// components/Message.tsx
import { Response } from './Response';
import { Avatar } from './Avatar';

interface MessageProps {
  message: {
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
  };
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <Avatar role={message.role} />

      <div className={`
        max-w-[65ch] rounded-2xl px-4 py-3
        ${isUser
          ? 'bg-blue-600 text-white rounded-br-sm ml-auto'
          : 'bg-gray-100 dark:bg-gray-800 rounded-bl-sm'
        }
      `}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <Response>{message.content}</Response>
        )}

        <time className="text-xs opacity-70 mt-2 block">
          {new Date(message.timestamp).toLocaleTimeString()}
        </time>
      </div>
    </div>
  );
}

export function StreamingMessage({ content }: { content: string }) {
  return (
    <div className="flex gap-3">
      <Avatar role="assistant" />

      <div className="max-w-[65ch] rounded-2xl rounded-bl-sm px-4 py-3 bg-gray-100 dark:bg-gray-800">
        <Response streaming>{content}</Response>
        <span className="inline-block w-2 h-5 bg-gray-600 animate-pulse ml-1" />
      </div>
    </div>
  );
}
```

### 4.3 Input Area Component

```typescript
// components/InputArea.tsx
import { useState, useRef, useEffect } from 'react';

interface InputAreaProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function InputArea({ onSend, disabled }: InputAreaProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [input]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || disabled) return;

    onSend(input);
    setInput('');
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="border-t p-4">
      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Shift+Enter for new line)"
          disabled={disabled}
          className="
            flex-1 resize-none rounded-lg border px-4 py-3
            focus:outline-none focus:ring-2 focus:ring-blue-500
            disabled:opacity-50 disabled:cursor-not-allowed
            max-h-48
          "
          rows={1}
        />

        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="
            px-6 py-3 bg-blue-600 text-white rounded-lg
            hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
          "
        >
          Send
        </button>
      </div>
    </form>
  );
}
```

### 4.4 Backend: Streaming Endpoint (Node.js)

```typescript
// server/api/chat.ts
import { openai } from '@ai-sdk/openai';
import { streamText } from 'ai';

export async function POST(req: Request) {
  const { messages } = await req.json();

  // Apply context management
  const optimizedMessages = await optimizeContext(messages);

  const result = streamText({
    model: openai('gpt-4'),
    messages: optimizedMessages,
    temperature: 0.7,
  });

  // Stream response
  return result.toTextStreamResponse();
}

async function optimizeContext(messages: Message[]): Promise<Message[]> {
  const tokenCount = estimateTokens(messages);

  if (tokenCount < 8000) {
    return messages; // Under budget, no optimization needed
  }

  // Apply compaction strategy
  const compactor = new ContextCompactor({
    maxTokens: 2000,
    tokenThreshold: 8000,
    retentionWindow: 6,
  });

  return await compactor.compact(messages);
}
```

---

## 5. Key Takeaways

### Modern UI (2025)
1. **Generous spacing** (16px between bubbles, 12-16px internal padding)
2. **Smooth streaming** (5ms/char with buffering, requestAnimationFrame)
3. **Robust markdown** (handle incomplete formatting during streaming)
4. **Dual-theme code blocks** (separate light/dark SyntaxHighlighter instances)
5. **Tool call visualization** (collapsible details, duration tracking)
6. **Virtual scrolling** for long conversations

### Context Management
1. **Hierarchical memory** (short/medium/long term with different strategies)
2. **Importance scoring** (semantic similarity + intrinsic importance + recency)
3. **Pattern-based compaction** (preserve semantic units, 90% reduction)
4. **Tool result compaction** (compact first, summarize later)
5. **External memory with RAG** (vector DB + key-value store)
6. **Token budget allocation** (explicit budgets per context type)

### Multi-Agent Systems
1. **Choose right pattern** (sequential/concurrent/handoff/magentic based on task)
2. **Minimize context handoffs** (1000-2000 token summaries between agents)
3. **Single message thread** for handoffs (no context reloading)
4. **Explicit handoff contracts** (structured payload with summary/context/task)
5. **Agent specialization** (clear domains, minimal context needs)
6. **LangGraph for efficiency** (2.2x faster, delta-based state management)

### Production Considerations
1. **Monitor token usage** per agent/operation
2. **Implement checkpointing** for recovery
3. **Measure compaction quality** (compression ratio, information retention)
4. **Use observability** (metrics, tracing, logging)
5. **Graceful degradation** when approaching limits
6. **Multi-mode compaction** (different strategies per task type)

---

## Sources

1. **UI Patterns**: bricxlabs.com (Chat UI Design Patterns), shadcn.io (AI Response Component), dev.to (Streaming Text), upstash.com (Smooth Streaming)

2. **Context Management**: anthropic.com (Effective Context Engineering), dev.to (Context Compaction), getmaxim.ai (Context Window Management), factory.ai (Context Window Problem)

3. **Multi-Agent**: learn.microsoft.com (AI Agent Design Patterns), cookbook.openai.com (Orchestrating Agents), arxiv.org (MCP for Multi-Agent Systems), forgecode.dev (Context Compaction)

4. **Tools/Visualization**: deepnlp.org (AgentBoard), ai-sdk.dev (Tool Calling)

---

**Document Version**: 1.0
**Created**: 2025-11-12
**Token Budget**: Approximately 12,000 tokens for complete reference