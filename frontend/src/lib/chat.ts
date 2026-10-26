/**

 * Intelligent Algorithm Chat & Streaming Engine for pebble.

 * Provides instant step-by-step algorithm walkthroughs, code visualizations,

 * and realistic token streaming simulation.

 */

import { request } from "./api.ts"

export const askPebble = (text: string, lang: 'python' | 'java' | 'cpp', signal?: AbortSignal) =>

  request<any>('/ask', { method: 'POST', body: { text, programming_language: lang }, signal });

export function formatAskResponse(r: any): string {

  const p: string[] = [];

  if (r.problem) p.push(`### ${r.problem.id}. ${r.problem.title}`);

  p.push(r.message);

  if (r.solution) p.push('```' + r.solution.language + '\n' + r.solution.code.trimEnd() + '\n```');

  if (r.candidates?.length) p.push('#### Did you mean?\n\n' + r.candidates.map((c: any) => `- ${c.id}. ${c.title}`).join('\n'));

  return p.join('\n\n');

}

export interface VisualStep {

  step: number;

  label: string;

  description: string;

  codeSnippet?: string;

  statePreview?: string;

}

export interface ChatMessage {

  id: string;

  role: 'user' | 'assistant';

  content: string;

  timestamp: number;

  visualSteps?: VisualStep[];

}

export interface ChatSession {

  id: string;

  title: string;

  createdAt: number;

  updatedAt: number;

  messages: ChatMessage[];

}

const CHAT_STORAGE_KEY = 'pebble_chats';

// Seed algorithmic knowledge base with visual step-by-step walkthroughs

// const ALGORITHM_KNOWLEDGE: Record<

//   string,

//   {

//     title: string;

//     content: string;

//     steps?: VisualStep[];

//   }

// > = {

//   'two sum': {

//     title: 'Two Sum (Hash Map & Two Pointers)',

//     content: `### Two Sum: Optimized $O(n)$ Solution

// Given an array of integers \`nums\` and an integer \`target\`, return the indices of the two numbers such that they add up to \`target\`.

// #### Key Insight

// Instead of checking every pair with nested loops ($O(n^2)$), use a **hash map** to store each number's index as you iterate. For each element \`x\`, check if the complement (\`target - x\`) was already seen.

// \`\`\`typescript

// function twoSum(nums: number[], target: number): number[] {

//   const seen = new Map<number, number>(); // value -> index

//   for (let i = 0; i < nums.length; i++) {

//     const complement = target - nums[i];

//     if (seen.has(complement)) {

//       return [seen.get(complement)!, i];

//     }

//     seen.set(nums[i], i);

//   }

//   return [];

// }

// \`\`\`

// #### Complexity Analysis

// - **Time Complexity:** $O(n)$ single pass lookup.

// - **Space Complexity:** $O(n)$ for the hash map storage.`,

//     steps: [

//       {

//         step: 1,

//         label: 'Initialize Lookup Table',

//         description: 'Create an empty hash map `seen` to store pairs of `number -> index`.',

//         statePreview: 'seen = {}',

//       },

//       {

//         step: 2,

//         label: 'Compute Complement',

//         description: 'For index 0 (val = 2, target = 9), complement = 9 - 2 = 7. Not in map.',

//         statePreview: 'seen = { 2: 0 }',

//       },

//       {

//         step: 3,

//         label: 'Match Found',

//         description: 'For index 1 (val = 7), complement = 9 - 7 = 2. Found 2 at index 0!',

//         statePreview: 'return [0, 1]',

//       },

//     ],

//   },

//   'binary search': {

//     title: 'Binary Search ($O(\\log n)$ Divide & Conquer)',

//     content: `### Binary Search on a Sorted Array

// Binary Search repeatedly divides the search interval in half. If the target value is less than the middle element, narrow the interval to the lower half; otherwise, narrow to the upper half.

// \`\`\`typescript

// function binarySearch(nums: number[], target: number): number {

//   let left = 0;

//   let right = nums.length - 1;

//   while (left <= right) {

//     // Avoid integer overflow with (left + right) >>> 1

//     const mid = left + Math.floor((right - left) / 2);

//     if (nums[mid] === target) {

//       return mid; // Target found

//     } else if (nums[mid] < target) {

//       left = mid + 1; // Discard left half

//     } else {

//       right = mid - 1; // Discard right half

//     }

//   }

//   return -1; // Target not present

// }

// \`\`\`

// #### Why it Works

// - Each iteration eliminates half of the remaining elements.

// - Halving $N$ items takes $\\log_2 N$ steps before 1 element remains.`,

//     steps: [

//       {

//         step: 1,

//         label: 'Set Pointers',

//         description: 'Place `left = 0` and `right = N - 1`.',

//         statePreview: 'left: [0] ... right: [N-1]',

//       },

//       {

//         step: 2,

//         label: 'Inspect Midpoint',

//         description: 'Compute `mid = left + (right - left) // 2`. Compare `nums[mid]` to `target`.',

//         statePreview: 'mid = 4 -> nums[mid] = 12',

//       },

//       {

//         step: 3,

//         label: 'Shrink Window',

//         description: 'If `target > nums[mid]`, search right half `left = mid + 1`. Else search left.',

//         statePreview: 'search space reduced by 50%',

//       },

//     ],

//   },

//   'merge sort': {

//     title: 'Merge Sort ($O(n \\log n)$ Stable Sort)',

//     content: `### Merge Sort: Divide, Conquer & Combine

// Merge Sort is a textbook example of recursive divide-and-conquer with guaranteed $O(n \\log n)$ time.

// \`\`\`python

// def merge_sort(arr: list[int]) -> list[int]:

//     if len(arr) <= 1:

//         return arr

//     mid = len(arr) // 2

//     left = merge_sort(arr[:mid])

//     right = merge_sort(arr[mid:])

//     return merge(left, right)

// def merge(left: list[int], right: list[int]) -> list[int]:

//     result = []

//     i = j = 0

//     while i < len(left) and j < len(right):

//         if left[i] <= right[j]:

//             result.append(left[i])

//             i += 1

//         else:

//             result.append(right[j])

//             j += 1

//     result.extend(left[i:])

//     result.extend(right[j:])

//     return result

// \`\`\`

// #### Step-by-Step Visualization

// 1. **Divide:** Recursively split the array down to individual 1-element arrays.

// 2. **Conquer:** A single element is already sorted.

// 3. **Combine:** Merge two sorted sub-lists by comparing front elements in $O(n)$ time.`,

//     steps: [

//       {

//         step: 1,

//         label: 'Split in Half',

//         description: '[8, 3, 5, 1] splits into [8, 3] and [5, 1].',

//         statePreview: '[8, 3] | [5, 1]',

//       },

//       {

//         step: 2,

//         label: 'Base Case Units',

//         description: 'Splits down to [8], [3], [5], [1].',

//         statePreview: '[8] [3] [5] [1]',

//       },

//       {

//         step: 3,

//         label: 'Merge & Sort',

//         description: 'Compare pointers and weave into [3, 8] and [1, 5] -> [1, 3, 5, 8].',

//         statePreview: '[1, 3, 5, 8] ✓ sorted',

//       },

//     ],

//   },

//   'dfs vs bfs': {

//     title: 'DFS vs. BFS Graph Traversal Comparison',

//     content: `### DFS vs BFS: How They Explore

// Both algorithms visit every vertex in a graph or tree in $O(V + E)$ time, but their spatial memory and visitation orders differ significantly.

// | Traversal | Data Structure | Best Used For | Memory |

// | :--- | :--- | :--- | :--- |

// | **BFS** (Breadth-First) | Queue (FIFO) | Shortest path in unweighted graphs | $O(\\text{width})$ |

// | **DFS** (Depth-First) | Stack / Recursion | Path existence, topological sort, cycle detection | $O(\\text{height})$ |

// \`\`\`typescript

// // BFS: Layer by Layer using Queue

// function bfs(graph: Map<string, string[]>, start: string): string[] {

//   const visited = new Set<string>([start]);

//   const queue = [start];

//   const order: string[] = [];

//   while (queue.length > 0) {

//     const node = queue.shift()!;

//     order.push(node);

//     for (const neighbor of graph.get(node) || []) {

//       if (!visited.has(neighbor)) {

//         visited.add(neighbor);

//         queue.push(neighbor);

//       }

//     }

//   }

//   return order;

// }

// \`\`\`

// #### Recommendation Rule

// - Need the **shortest distance** or closest node? Always pick **BFS**.

// - Need to explore **all permutations, exhaust paths, or solve mazes**? Pick **DFS**.`,

//     steps: [

//       {

//         step: 1,

//         label: 'BFS Queue Push',

//         description: 'Enqueues current level before moving to child levels.',

//         statePreview: 'Q = [root] -> Level 0',

//       },

//       {

//         step: 2,

//         label: 'BFS Ripple Outward',

//         description: 'Discovers all distance 1 nodes, then distance 2 nodes.',

//         statePreview: 'Radius expands concentrically',

//       },

//       {

//         step: 3,

//         label: 'DFS Deep Dive',

//         description: 'Dives down the left-most branch until leaf before backtracking.',

//         statePreview: 'Stack: [A -> B -> D] then backtrack to C',

//       },

//     ],

//   },

// };

/**

 * Retrieves persisted chat history from localStorage.

 */

export function loadChatSessions(): ChatSession[] {

  try {

    if (typeof window !== 'undefined' && window.localStorage) {

      const raw = window.localStorage.getItem(CHAT_STORAGE_KEY);

      if (raw) {

        return JSON.parse(raw);

      }

    }

  } catch {

    // Return empty list on parse error or private mode

  }

  return [];

}

/**

 * Persists chat sessions.

 */

export function saveChatSessions(sessions: ChatSession[]): void {

  try {

    if (typeof window !== 'undefined' && window.localStorage) {

      window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(sessions));

    }

  } catch {

    // Fail silently

  }

}

/**

 * Creates a new empty chat session.

 */

export function createChatSession(initialTitle = 'New conversation'): ChatSession {

  return {

    id: `chat_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,

    title: initialTitle,

    createdAt: Date.now(),

    updatedAt: Date.now(),

    messages: [],

  };

}