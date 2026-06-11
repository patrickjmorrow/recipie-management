export interface RecipeMetadata {
  prep_time?: number
  cook_time?: number
  servings?: number
  difficulty?: 'easy' | 'medium' | 'hard'
}

export interface TagResponse {
  id: string
  name: string
  deprecated_at: string | null
}

export interface IngredientResponse {
  id: string
  name: string
}

export interface RecipeIngredientResponse {
  id: string
  ingredient: IngredientResponse
  quantity: number | null
  unit: string | null
  note: string | null
  sort_order: number
}

export interface RecipeSummary {
  id: string
  author_id: string | null
  title: string
  description: string | null
  image_key: string | null
  recipie_metadata: RecipeMetadata | null
  tags: TagResponse[]
  avg_rating: number | null
  review_count: number
  created_at: string
  updated_at: string
}

export interface RecipeResponse extends RecipeSummary {
  instructions: string | null
  recipe_ingredients: RecipeIngredientResponse[]
}

export interface RecipeIngredientCreate {
  ingredient_name: string
  quantity?: number
  unit?: string
  note?: string
  sort_order: number
}

export interface RecipeCreate {
  title: string
  description?: string
  instructions?: string
  image_key?: string
  recipie_metadata?: RecipeMetadata
  recipe_ingredients: RecipeIngredientCreate[]
  tag_ids: string[]
}

export type RecipeUpdate = Partial<RecipeCreate>

export interface ReviewResponse {
  id: string
  recipe_id: string
  reviewer_id: string
  reviewer_display_name: string
  rating: number
  body: string | null
  created_at: string
  updated_at: string
}

export interface ReviewCreate {
  rating: number
  body?: string
}

export interface ReviewUpdate {
  rating?: number
  body?: string
}

export interface UserResponse {
  id: string
  email: string
  display_name: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
