import { KaggleAI } from './KaggleAI';

class AICore {
  private kaggleAI: KaggleAI;

  constructor() {
    this.kaggleAI = new KaggleAI();
  }

  async initialize() {
    try {
      await this.kaggleAI.initialize();
    } catch (error) {
      console.error('Failed to initialize KaggleAI:', error);
      throw error;
    }
  }

  async processInput(query: string, forceVariation: boolean = false) {
    try {
      return await this.kaggleAI.generateResponse(query);
    } catch (error) {
      console.error('Error processing input:', error);
      throw error;
    }
  }

  async processThread(messages: any[]) {
    try {
      return await this.kaggleAI.processThread(messages);
    } catch (error) {
      console.error('Error processing thread:', error);
      throw error;
    }
  }
}

export default AICore;