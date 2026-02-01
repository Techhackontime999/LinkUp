import os

content = """{% extends "base.html" %}

{% block content %}
<div class="grid grid-cols-1 md:grid-cols-4 gap-6 pt-6">
    <!-- Left Sidebar -->
    <div class="md:col-span-1">
        <div class="premium-card p-0 overflow-hidden animate-fade-in">
            <div class="bg-gradient-primary h-16"></div>
            <div class="px-6 pb-6">
                <div class="-mt-10 mb-4">
                    <div class="avatar-gradient inline-block">
                        <div class="avatar-inner">
                            <div
                                class="flex items-center justify-center w-20 h-20 rounded-full bg-gradient-primary text-white font-bold text-2xl">
                                {{ user.username|slice:":2"|upper }}
                            </div>
                        </div>
                    </div>
                </div>
                <h2 class="text-xl font-bold text-gray-800 mb-1">{{ user.username }}</h2>
                <p class="text-sm text-gray-600 mb-4">{{ user.profile.headline|default:"Full Stack Developer" }}</p>
                <div class="border-t border-gray-100 pt-4 space-y-2">
                    <div class="flex justify-between items-center text-sm">
                        <span class="text-gray-600">Profile viewers</span>
                        <span class="font-semibold text-purple-600">127</span>
                    </div>
                    <div class="flex justify-between items-center text-sm">
                        <span class="text-gray-600">Post impressions</span>
                        <span class="font-semibold text-purple-600">1,459</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Feed -->
    <div class="md:col-span-2">
        <!-- Post Creation Card -->
        <div class="premium-card p-5 mb-6 animate-fade-in">
            <form action="" method="post" enctype="multipart/form-data">
                {% csrf_token %}
                <div class="flex items-start space-x-3 mb-3">
                    <div class="avatar-gradient">
                        <div class="avatar-inner">
                            <div
                                class="flex items-center justify-center w-12 h-12 rounded-full bg-gradient-primary text-white font-semibold">
                                {{ user.username|slice:":2"|upper }}
                            </div>
                        </div>
                    </div>
                    <div class="flex-1">
                        <textarea name="content" rows="3"
                            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-purple-400 focus:ring-2 focus:ring-purple-100 transition-all resize-none"
                            placeholder="Share your thoughts...">{{ form.content.value|default:"" }}</textarea>
                    </div>
                </div>
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4">
                        <label
                            class="flex items-center space-x-2 px-4 py-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-blue-500" fill="none"
                                viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                            <span class="text-sm font-medium text-gray-700">Photo</span>
                            <input type="file" name="image" class="hidden" accept="image/*">
                        </label>
                    </div>
                    <button type="submit" class="btn-premium px-6 py-2.5 text-sm">Share Post</button>
                </div>
            </form>
        </div>

        <!-- Posts Feed -->
        {% for post in posts %}
        <div class="post-card animate-fade-in">
            <div class="post-author">
                <div class="post-avatar">
                    {{ post.user.username|slice:":2"|upper }}
                </div>
                <div class="flex-1">
                    <div class="flex items-center justify-between">
                        <div>
                            <h3 class="font-bold text-gray-800 hover:text-purple-600 transition-colors">
                                <a href="{% url 'public_profile' post.user.username %}">{{ post.user.username }}</a>
                            </h3>
                            <p class="text-xs text-gray-500">{{ post.created_at|timesince }} ago</p>
                        </div>
                        {% if post.user != request.user %}
                        <button class="btn-follow {% if post.user in request.user.following.all.followers %}following{% else %}not-following{% endif %} px-4 py-1.5 text-xs"
                            data-user-id="{{ post.user.id }}">
                            <span class="follow-text">{% if post.user in request.user.following.all.followers %}Following{% else %}Follow{% endif %}</span>
                        </button>
                        {% endif %}
                    </div>
                </div>
                <button class="text-gray-400 hover:text-gray-600 transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24"
                        stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M5 12h.01M12 12h.01M19 12h.01M6 12a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0zm7 0a1 1 0 11-2 0 1 1 0 012 0z" />
                    </svg>
                </button>
            </div>

            <div class="post-content">{{ post.content }}</div>

            {% if post.image %}
            <div class="post-image">
                <img src="{{ post.image.url }}" alt="Post image" class="w-full h-auto" />
            </div>
            {% endif %}

            <div class="flex items-center justify-between pt-3 border-t border-gray-100">
                <button class="like-btn {% if request.user in post.likes.all %}liked{% endif %}"
                    data-post-id="{{ post.id }}">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5"
                        fill="{% if request.user in post.likes.all %}currentColor{% else %}none{% endif %}"
                        viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                    </svg>
                    <span class="like-count font-medium">{{ post.total_likes }}</span>
                </button>
                <button
                    class="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors text-gray-600">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24"
                        stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <span class="text-sm font-medium">Comment</span>
                </button>
                <button
                    class="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors text-gray-600">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24"
                        stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                    </svg>
                    <span class="text-sm font-medium">Share</span>
                </button>
            </div>
        </div>
        {% empty %}
        <div class="premium-card p-12 text-center animate-fade-in">
            <div class="mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto text-gray-300" fill="none"
                    viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-700 mb-2">No posts yet</h3>
            <p class="text-gray-500">Be the first to share something amazing!</p>
        </div>
        {% endfor %}
    </div>

    <!-- Right Sidebar -->
    <div class="md:col-span-1">
        <div class="premium-card p-5 animate-fade-in">

            <h3 class="text-lg font-bold text-gray-800 mb-4">Trending Topics</h3>
            <div class="space-y-4">
                <div class="hover-lift cursor-pointer p-3 rounded-lg transition-all">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-gray-500 text-xs">#WebDevelopment</span>
                        <span class="text-xs font-semibold text-purple-600">2.4k posts</span>
                    </div>
                    <p class="text-sm font-medium text-gray-700">Latest trends in web development</p>
                </div>
                <!-- ... -->
            </div>
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        const likeBtns = document.querySelectorAll('.like-btn');
        likeBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                const postId = this.dataset.postId;
                const likeCountSpan = this.querySelector('.like-count');
                const svgIcon = this.querySelector('svg');
                fetch(`/like/${postId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}',
                        'Content-Type': 'application/json'
                    },
                })
                .then(response => response.json())
                .then(data => {
                    likeCountSpan.textContent = data.likes_count;
                    if (data.is_liked) {
                        svgIcon.setAttribute('fill', 'currentColor');
                        this.classList.add('liked');
                    } else {
                        svgIcon.setAttribute('fill', 'none');
                        this.classList.remove('liked');
                    }
                });
            });
        });

        const followBtns = document.querySelectorAll('.btn-follow');
        followBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                const userId = this.dataset.userId;
                const textSpan = this.querySelector('.follow-text');
                fetch(`/network/follow/${userId}/?ajax=1`)
                .then(response => response.json())
                .then(data => {
                    if (data.is_following) {
                        this.classList.replace('not-following', 'following');
                        textSpan.textContent = 'Following';
                    } else {
                        this.classList.replace('following', 'not-following');
                        textSpan.textContent = 'Follow';
                    }
                });
            });
        });
    });
</script>
{% endblock %}
"""

with open('feed/templates/feed/index.html', 'w') as f:
    f.write(content)
