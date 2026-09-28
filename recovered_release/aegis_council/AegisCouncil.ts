export interface AgentReport {
  result: any;
  explanation: string;
  influence: Record<string, number>;
}

export abstract class AegisAgent {
  protected name: string;
  protected memory: any;
  protected result: any = {};
  protected explanation: string = '';
  protected influence: Record<string, number> = {};

  constructor(name: string, memory: any) {
    this.name = name;
    this.memory = memory;
  }

  abstract analyze(inputData: Record<string, any>): Promise<void>;
  abstract report(): AgentReport;

  getName(): string {
    return this.name;
  }
}

export class AegisCouncil {
  private agents: Map<string, AegisAgent> = new Map();
  private memory: any;
  private reports: AgentReport[] = [];

  constructor() {
    this.memory = {
      write: async (key: string, value: any, weight: number = 0.5) => {
        console.log(`Memory write: ${key}`);
        return key;
      },
      read: async (key: string) => {
        console.log(`Memory read: ${key}`);
        return null;
      },
      audit: () => ({})
    };
  }

  registerAgent(agent: AegisAgent): void {
    this.agents.set(agent.getName(), agent);
    console.log(`Registered agent: ${agent.getName()}`);
  }

  async dispatch(inputData: Record<string, any>): Promise<boolean> {
    this.reports = [];
    
    try {
      for (const agent of this.agents.values()) {
        await agent.analyze(inputData);
        this.reports.push(agent.report());
      }
      return true;
    } catch (error) {
      console.error('Aegis Council dispatch failed:', error);
      return false;
    }
  }

  getReports(): AgentReport[] {
    return this.reports;
  }
}

// Export agent classes for use in other files
export class MetaJudgeAgent extends AegisAgent {
  constructor(name: string, memory: any) {
    super(name, memory);
  }

  async analyze(inputData: Record<string, any>): Promise<void> {
    this.result = { decision: 'approved', confidence: 0.85 };
    this.explanation = 'MetaJudge analysis completed';
  }

  report(): AgentReport {
    return {
      result: this.result,
      explanation: this.explanation,
      influence: this.influence
    };
  }
}

export class TemporalAgent extends AegisAgent {
  constructor(name: string, memory: any) {
    super(name, memory);
  }

  async analyze(inputData: Record<string, any>): Promise<void> {
    this.result = { forecast: 'stable', timeline: 'short-term' };
    this.explanation = 'Temporal analysis completed';
  }

  report(): AgentReport {
    return {
      result: this.result,
      explanation: this.explanation,
      influence: this.influence
    };
  }
}

export class VirtueAgent extends AegisAgent {
  constructor(name: string, memory: any) {
    super(name, memory);
  }

  async analyze(inputData: Record<string, any>): Promise<void> {
    this.result = { 
      virtues: { compassion: 0.8, integrity: 0.9, wisdom: 0.7 },
      overall: 0.8 
    };
    this.explanation = 'Virtue analysis completed';
  }

  report(): AgentReport {
    return {
      result: this.result,
      explanation: this.explanation,
      influence: this.influence
    };
  }
}