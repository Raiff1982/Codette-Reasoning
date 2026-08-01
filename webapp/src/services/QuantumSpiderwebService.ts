import { supabase } from '@/lib/supabase';

export interface CocoonMemory {
  id: string;
  user_id: string;
  title: string;
  summary: string;
  quote: string;
  emotion: string;
  tags: string[];
  intensity: number;
  encrypted: boolean;
  metadata?: any;
  created_at: string;
  updated_at: string;
}

export interface EmotionalWeb {
  id: string;
  user_id: string;
  emotion: string;
  nodes: any[];
  connections: any[];
  quantum_state: number[];
  created_at: string;
  updated_at: string;
}

export class QuantumSpiderwebService {
  // Cocoon Management - Updated to use quantum_cocoons table
  async getCocoons(filters?: {
    emotion?: string;
    encrypted?: boolean;
    search?: string;
  }): Promise<CocoonMemory[]> {
    let query = supabase
      .from('quantum_cocoons')
      .select('*')
      .order('created_at', { ascending: false });

    if (filters?.emotion && filters.emotion !== 'all') {
      query = query.eq('emotion', filters.emotion);
    }

    if (filters?.encrypted !== undefined) {
      query = query.eq('encrypted', filters.encrypted);
    }

    if (filters?.search) {
      query = query.or(`title.ilike.%${filters.search}%,summary.ilike.%${filters.search}%`);
    }

    const { data, error } = await query;

    if (error) {
      throw new Error(`Failed to fetch cocoons: ${error.message}`);
    }

    return data || [];
  }

  async createCocoon(cocoon: Omit<CocoonMemory, 'id' | 'user_id' | 'created_at' | 'updated_at'>): Promise<CocoonMemory> {
    const { data, error } = await supabase
      .from('quantum_cocoons')
      .insert([cocoon])
      .select()
      .single();

    if (error) {
      throw new Error(`Failed to create cocoon: ${error.message}`);
    }

    return data;
  }

  async updateCocoon(id: string, updates: Partial<CocoonMemory>): Promise<CocoonMemory> {
    const { data, error } = await supabase
      .from('quantum_cocoons')
      .update(updates)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      throw new Error(`Failed to update cocoon: ${error.message}`);
    }

    return data;
  }

  async deleteCocoon(id: string): Promise<void> {
    const { error } = await supabase
      .from('quantum_cocoons')
      .delete()
      .eq('id', id);

    if (error) {
      throw new Error(`Failed to delete cocoon: ${error.message}`);
    }
  }

  // Emotional Web Management
  async getEmotionalWebs(): Promise<EmotionalWeb[]> {
    const { data, error } = await supabase
      .from('emotional_webs')
      .select('*')
      .order('created_at', { ascending: false });

    if (error) {
      throw new Error(`Failed to fetch emotional webs: ${error.message}`);
    }

    return data || [];
  }

  async getEmotionalWebByEmotion(emotion: string): Promise<EmotionalWeb | null> {
    const { data, error } = await supabase
      .from('emotional_webs')
      .select('*')
      .eq('emotion', emotion)
      .single();

    if (error && error.code !== 'PGRST116') { // PGRST116 is "not found"
      throw new Error(`Failed to fetch emotional web: ${error.message}`);
    }

    return data;
  }

  async createOrUpdateEmotionalWeb(web: Omit<EmotionalWeb, 'id' | 'user_id' | 'created_at' | 'updated_at'>): Promise<EmotionalWeb> {
    // First try to get existing web
    const existing = await this.getEmotionalWebByEmotion(web.emotion);

    if (existing) {
      // Update existing web
      const { data, error } = await supabase
        .from('emotional_webs')
        .update({
          nodes: web.nodes,
          connections: web.connections,
          quantum_state: web.quantum_state
        })
        .eq('id', existing.id)
        .select()
        .single();

      if (error) {
        throw new Error(`Failed to update emotional web: ${error.message}`);
      }

      return data;
    } else {
      // Create new web
      const { data, error } = await supabase
        .from('emotional_webs')
        .insert([web])
        .select()
        .single();

      if (error) {
        throw new Error(`Failed to create emotional web: ${error.message}`);
      }

      return data;
    }
  }

  // Quantum Operations
  async performQuantumWalk(emotion: string): Promise<CocoonMemory | null> {
    const cocoons = await this.getCocoons({ emotion });
    
    if (cocoons.length === 0) {
      return null;
    }

    // Quantum-inspired selection with probability weights
    const weights = cocoons.map(cocoon => 
      cocoon.intensity * (1 + Math.random())
    );
    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
    const random = Math.random() * totalWeight;
    
    let selectedCocoon = cocoons[0];
    let currentWeight = 0;
    
    for (let i = 0; i < cocoons.length; i++) {
      currentWeight += weights[i];
      if (random <= currentWeight) {
        selectedCocoon = cocoons[i];
        break;
      }
    }

    return selectedCocoon;
  }

  async buildEmotionalWeb(emotion: string): Promise<EmotionalWeb> {
    const cocoons = await this.getCocoons({ emotion });
    
    // Build nodes and connections
    const nodes = cocoons.map(cocoon => ({
      id: cocoon.id,
      title: cocoon.title,
      intensity: cocoon.intensity,
      tags: cocoon.tags
    }));

    // Create connections based on shared tags
    const connections: any[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const sharedTags = nodes[i].tags.filter(tag => 
          nodes[j].tags.includes(tag)
        );
        
        if (sharedTags.length > 0) {
          connections.push({
            source: nodes[i].id,
            target: nodes[j].id,
            strength: sharedTags.length / Math.max(nodes[i].tags.length, nodes[j].tags.length),
            sharedTags
          });
        }
      }
    }

    // Generate quantum state
    const quantum_state = Array.from({ length: 3 }, () => Math.random());

    const webData = {
      emotion,
      nodes,
      connections,
      quantum_state
    };

    return await this.createOrUpdateEmotionalWeb(webData);
  }

  // Export/Import Operations
  async exportCocoons(filters?: any): Promise<any> {
    const cocoons = await this.getCocoons(filters);
    const webs = await this.getEmotionalWebs();

    return {
      quantum_cocoons: cocoons,
      emotional_webs: webs,
      metadata: {
        total_cocoons: cocoons.length,
        total_webs: webs.length,
        export_timestamp: new Date().toISOString(),
        filters
      }
    };
  }

  async importCocoons(data: any): Promise<void> {
    if (data.quantum_cocoons && Array.isArray(data.quantum_cocoons)) {
      for (const cocoon of data.quantum_cocoons) {
        const { id, user_id, created_at, updated_at, ...cocoonData } = cocoon;
        await this.createCocoon(cocoonData);
      }
    }

    if (data.emotional_webs && Array.isArray(data.emotional_webs)) {
      for (const web of data.emotional_webs) {
        const { id, user_id, created_at, updated_at, ...webData } = web;
        await this.createOrUpdateEmotionalWeb(webData);
      }
    }
  }
}

export const quantumSpiderwebService = new QuantumSpiderwebService();